// 人工批注与标注管理端到端测试（task_13 D4/D5/D6）
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_item.dart';
import 'package:ai_reader_frontend/features/annotation/presentation/annotation_manager.dart';
import 'package:ai_reader_frontend/features/annotation/presentation/annotation_palette.dart';
import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';
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

  /// 从 RenderEditable 渲染树收集指定装饰线型的文本
  String decoratedTextOf(Iterable<RenderEditable> editables, TextDecorationStyle style) {
    final buf = StringBuffer();
    void walk(TextSpan span) {
      if (span.style?.decorationStyle == style) buf.write(span.toPlainText());
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

  testWidgets('划词→标注面板→波浪线：子串获得波浪装饰线', (tester) async {
    await pumpDesktopApp(tester);

    final paragraphFinder = find.textContaining('现代分布式系统').first;
    final paraRect = tester.getRect(paragraphFinder);
    final gesture = await tester.startGesture(paraRect.center - const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 700));
    await gesture.moveBy(const Offset(160, 0));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();

    // 胶囊第 6 按钮「标注」打开面板
    await tester.tap(find.text('标注'));
    await tester.pumpAndSettle();
    expect(find.byType(AnnotationPalette), findsOneWidget);

    await tester.tap(find.text('波浪线'));
    await tester.pumpAndSettle();
    // 两维交互（验收定稿）：样式仅选择，显式点「应用」提交组合
    await tester.tap(find.byKey(const ValueKey('palette_apply')));
    await tester.pumpAndSettle();

    final editables =
        tester.allElements.map((e) => e.renderObject).whereType<RenderEditable>();
    final wavy = decoratedTextOf(editables, TextDecorationStyle.wavy);
    expect(wavy, isNotEmpty, reason: '波浪线应作用于所选子串');
    expect(wavy.length, lessThan(60), reason: '不应整段装饰');
  });

  testWidgets('人工批注：选区→批注→输入→保存→计数行出现且 list 含 note', (tester) async {
    await pumpDesktopApp(tester);

    final paragraphFinder = find.textContaining('现代分布式系统').first;
    final paraRect = tester.getRect(paragraphFinder);
    final gesture = await tester.startGesture(paraRect.center - const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 700));
    await gesture.moveBy(const Offset(160, 0));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();

    await tester.tap(find.text('标注'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('批注'));
    await tester.pumpAndSettle();

    // 输入批注并保存
    await tester.enterText(find.byType(TextField), '这一段是人工批注的核心结论');
    await tester.tap(find.text('保存批注'));
    await tester.pumpAndSettle();

    expect(find.textContaining('1 条批注'), findsOneWidget, reason: '段落下方应出现批注计数');
  });

  testWidgets('标注管理器：列出/编辑/删除标注', (tester) async {
    var deletedId = '';
    String? editedId;
    String? editedNote;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: AnnotationManagerModal(
          entries: const [
            AnnotationListEntry(
              item: AnnotationItem(
                id: 'a1',
                bookId: 1,
                paragraphId: 'p1',
                startOffset: 0,
                endOffset: 6,
                style: AnnotationStyle.wavy,
                colorHex: '#34C759',
                noteText: '批注内容',
              ),
              excerpt: '被标注的原文片段',
            ),
          ],
          onDelete: (id) => deletedId = id,
          onEdit: (id, note) {
            editedId = id;
            editedNote = note;
          },
          onClose: () {},
        ),
      ),
    ));

    expect(find.text('被标注的原文片段'), findsOneWidget);
    expect(find.text('批注内容'), findsOneWidget);
    expect(find.textContaining('波浪线'), findsOneWidget);

    // 编辑入口携带 id 与当前批注原文（task_16）
    await tester.tap(find.byTooltip('编辑标注 a1'));
    expect(editedId, 'a1');
    expect(editedNote, '批注内容');

    await tester.tap(find.byTooltip('删除标注 a1'));
    expect(deletedId, 'a1');
  });

  testWidgets('批注编辑全链：新建→打开管理器→编辑→保存→列表更新', (tester) async {
    await pumpDesktopApp(tester);

    // 1. 划词创建批注
    final paragraphFinder = find.textContaining('现代分布式系统').first;
    final paraRect = tester.getRect(paragraphFinder);
    final gesture = await tester.startGesture(paraRect.center - const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 700));
    await gesture.moveBy(const Offset(160, 0));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();
    await tester.tap(find.text('标注'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('批注'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '旧批注文本');
    await tester.tap(find.text('保存批注'), warnIfMissed: true);
    await tester.pumpAndSettle();
    // 2. 打开管理器 → 编辑（mock 注解 id 带时间戳，用谓词匹配 Tooltip）
    await tester.tap(find.textContaining('1 条批注'));
    await tester.pumpAndSettle();
    final editTooltipFinder = find.byWidgetPredicate((w) =>
        w is Tooltip && (w.message?.startsWith('编辑标注') ?? false));
    await tester.tap(editTooltipFinder);
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsOneWidget, reason: '编辑器应打开且唯一');
    // 编辑器预填原文（管理器底下的行也显示同文本，故断言输入框内容而非全局文本）
    final editor = tester.widget<TextField>(find.byType(TextField));
    expect(editor.controller?.text, '旧批注文本');

    // 3. 修改并保存
    await tester.enterText(find.byType(TextField), '新批注文本');
    await tester.tap(find.text('保存批注'));
    await tester.pumpAndSettle();
    expect(find.text('新批注文本'), findsOneWidget, reason: '管理器应显示更新后的批注');
    expect(find.text('旧批注文本'), findsNothing);
  });
}
