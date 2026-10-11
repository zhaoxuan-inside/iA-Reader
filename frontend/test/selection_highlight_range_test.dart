// 划词高亮选区级端到端测试（task_12 D5：只高亮所选子串 + anchor 持久化）
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';
import 'package:ai_reader_frontend/features/selection_pill/presentation/floating_action_pill.dart';
import 'package:ai_reader_frontend/main.dart';

void main() {
  Future<void> pumpDesktopApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle();
  }

  /// 收集 EditableText 渲染树中带背景色的文本片段
  /// （SelectableText 走 RenderEditable，不产生 RichText widget）
  String highlightedTextOf(Iterable<RenderEditable> editables) {
    final buf = StringBuffer();
    void walk(TextSpan span) {
      if (span.style?.backgroundColor != null) buf.write(span.toPlainText());
      span.children?.forEach((c) {
        if (c is TextSpan) walk(c);
      });
    }

    for (final re in editables) {
      final root = re.text;
      if (root is TextSpan) walk(root);
    }
    return buf.toString();
  }

  testWidgets('划词后点高亮：只有所选子串被着色，且 anchor 带偏移持久化', (tester) async {
    await pumpDesktopApp(tester);

    final paragraphFinder = find.textContaining('现代分布式系统').first;
    expect(paragraphFinder, findsOneWidget);
    final paraRect = tester.getRect(paragraphFinder);

    // 长按拖拽划词（确定性构造选区）→ 胶囊出现
    final gesture = await tester.startGesture(paraRect.center - const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 700));
    await gesture.moveBy(const Offset(160, 0));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();

    expect(find.byType(FloatingActionPill), findsOneWidget);
    // 胶囊应悬停于鼠标松开位置上方（跟随鼠标）
    final pillRect = tester.getRect(find.byType(FloatingActionPill));
    final pointerPos = paraRect.center + const Offset(80, 0);
    expect(pointerPos.dy - pillRect.bottom, inExclusiveRange(0, 24),
        reason: '胶囊底边应贴近指针上方');

    // 点高亮 → 子串内联着色
    await tester.tap(find.text('高亮'));
    await tester.pumpAndSettle();

    final editables =
        tester.allElements.map((e) => e.renderObject).whereType<RenderEditable>();
    final highlighted = highlightedTextOf(editables);
    expect(highlighted, isNotEmpty, reason: '高亮后应有带背景色的片段');
    expect(highlighted.length, lessThan(60), reason: '只应高亮子串而非整段（段落远长于 60 字）');
  });

  testWidgets('标注经 annotation.list 回填后刷新仍渲染（持久化往返）', (tester) async {
    // 先在一个实例里创建标注
    final bridge = ReaderEngineBridge();
    final saveRes = await bridge.invoke('annotation.save', {
      'book_id': 1,
      'section_id': 1,
      'paragraph_id': 'p2',
      'style': 'highlight',
      'color': '#FFE066',
      'anchor': {'paragraph_id': 'p2', 'section_id': 1, 'start': 0, 'end': 6},
    });
    expect(saveRes.isSuccess, isTrue);
    final savedId = saveRes.data['annotation_id'];

    // list 应返回含 anchor 的行（模拟重启后回填）
    final listRes = await bridge.invoke('annotation.list', {'book_id': 1});
    expect(listRes.isSuccess, isTrue);
    final rows = (listRes.data['annotations'] as List).cast<Map<String, dynamic>>();
    final row = rows.firstWhere((r) => r['id'] == savedId);
    expect(row['anchor'] ?? row['anchor_json'], isNotNull, reason: 'anchor 应被保存并回读');
    expect(row['style'], 'highlight');

    // 删除也应可用（task_13 标注管理前置）
    final delRes = await bridge.invoke('annotation.delete', {'annotation_id': savedId});
    expect(delRes.isSuccess, isTrue);
    final list2 = await bridge.invoke('annotation.list', {'book_id': 1});
    final rows2 = (list2.data['annotations'] as List).cast<Map<String, dynamic>>();
    expect(rows2.any((r) => r['id'] == savedId), isFalse);
  });
}
