// 划词高亮选区级端到端测试（task_12 D5：只高亮所选子串 + anchor 持久化）
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
    // 桥接为单例：清空跨用例共享的内存 mock 状态
    ReaderEngineBridge().resetMockStateForTest();
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

    // 删除与更新也应可用（task_13/16 标注管理）
    final delRes = await bridge.invoke('annotation.deleted', {'annotation_id': savedId});
    expect(delRes.isSuccess, isTrue);
    final list2 = await bridge.invoke('annotation.list', {'book_id': 1});
    final rows2 = (list2.data['annotations'] as List).cast<Map<String, dynamic>>();
    expect(rows2.any((r) => r['id'] == savedId), isFalse);
  });

  testWidgets('annotation.update 部分更新批注文本（mock 往返）', (tester) async {
    final bridge = ReaderEngineBridge();
    final saveRes = await bridge.invoke('annotation.save', {
      'book_id': 1,
      'paragraph_id': 'p1',
      'style': 'margin_note',
      'note_text': '旧批注',
      'color': '#CA8A04',
    });
    final id = saveRes.data['annotation_id'];

    final updRes = await bridge.invoke('annotation.updated', {
      'annotation_id': id,
      'note_text': '新批注',
    });
    expect(updRes.isSuccess, isTrue);
    expect(updRes.data['status'], 'updated');

    final listRes = await bridge.invoke('annotation.list', {'book_id': 1});
    final rows = (listRes.data['annotations'] as List).cast<Map<String, dynamic>>();
    final row = rows.firstWhere((r) => r['id'] == id);
    expect(row['note_text'], '新批注');
    expect(row['color'], '#CA8A04', reason: '未提供的字段保持');

    // 更新不存在的 id → not_found
    final miss = await bridge.invoke('annotation.updated', {
      'annotation_id': 'no_such',
      'note_text': 'x',
    });
    expect(miss.data['status'], 'not_found');
  });

  testWidgets('流式伴读 mock：start 即 done，poll 稳定返回终态（task_17）', (tester) async {
    final bridge = ReaderEngineBridge();
    final startRes = await bridge.invoke('ai.companion_start', {
      'book_id': 1,
      'template_type': 'general',
      'selected_text': '预写式日志',
    });
    expect(startRes.isSuccess, isTrue);
    final requestId = startRes.data['request_id'] as String?;
    expect(requestId, isNotNull);
    expect(requestId!, isNotEmpty);

    final poll = await bridge.invoke('ai.companion_poll', {'request_id': requestId});
    expect(poll.isSuccess, isTrue);
    expect(poll.data['done'], isTrue);
    expect((poll.data['partial'] as String), contains('通俗解读'));
    // 重复 poll 稳定
    final poll2 = await bridge.invoke('ai.companion_poll', {'request_id': requestId});
    expect(poll2.data['done'], isTrue);

    // 未知 id 报错
    final miss = await bridge.invoke('ai.companion_poll', {'request_id': 'no_such'});
    expect(miss.isSuccess, isFalse);
  });
}
