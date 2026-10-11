import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/main.dart';
import 'package:ai_reader_frontend/core/theme/reader_theme.dart';
import 'package:ai_reader_frontend/features/selection_pill/presentation/floating_action_pill.dart';
import 'package:ai_reader_frontend/features/reader/presentation/controllers/focus_mode_controller.dart';
import 'package:ai_reader_frontend/features/library/presentation/library_screen.dart';
import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('FocusModeController Unit Tests', () {
    test('FocusModeController initial state is unfocused', () {
      final controller = FocusModeController();
      expect(controller.isFocusModeEnabled, false);
      expect(controller.getParagraphOpacity('p1'), 1.0);
      expect(controller.getParagraphOpacity('p2'), 1.0);
    });

    test('FocusModeController dims unfocused paragraphs to 0.65', () {
      final controller = FocusModeController();
      controller.focusParagraph('p2', selectedText: 'focused test');
      expect(controller.isFocusModeEnabled, true);
      expect(controller.activeParagraphId, 'p2');
      expect(controller.getParagraphOpacity('p2'), 1.0);
      expect(controller.getParagraphOpacity('p1'), ReaderTheme.focusDimOpacity);
      expect(controller.getParagraphOpacity('p3'), 0.65);

      // exit focus mode restores 1.0
      controller.exitFocusMode();
      expect(controller.isFocusModeEnabled, false);
      expect(controller.getParagraphOpacity('p1'), 1.0);
    });
  });

  group('FloatingActionPill Widget Tests', () {
    testWidgets('Renders all 5 cognitive & highlight buttons', (tester) async {
      CognitiveTemplateType? selected;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: FloatingActionPill(
              onTemplateSelected: (t) => selected = t,
            ),
          ),
        ),
      );

      expect(find.text('⚡️ 通俗'), findsOneWidget);
      expect(find.text('🔗 逻辑'), findsOneWidget);
      expect(find.text('🧐 批判'), findsOneWidget);
      expect(find.text('📖 术语'), findsOneWidget);
      expect(find.text('🖍 高亮'), findsOneWidget);

      await tester.tap(find.text('🔗 逻辑'));
      expect(selected, CognitiveTemplateType.logic);
    });
  });

  group('ReaderEngineBridge Action Tests', () {
    test('Bridge handles companion and annotation actions', () async {
      final bridge = ReaderEngineBridge();

      final resAsk = await bridge.invoke('ai.companion_ask', {
        'template_type': 'logic',
        'selected_text': 'test bridge text',
      });
      expect(resAsk.isSuccess, true);
      expect(resAsk.data['template_type'], 'logic');

      final resSave = await bridge.invoke('annotation.save', {
        'note_text': 'sample saved note',
      });
      expect(resSave.isSuccess, true);
      expect(resSave.data['status'], anyOf('persisted', 'saved'));

      final resList = await bridge.invoke('annotation.list', {'book_id': 1});
      expect(resList.isSuccess, true);
      final notes = resList.data['annotations'] as List;
      expect(notes.isNotEmpty, true);
    });
  });

  group('Decoupled Architecture & Workbench Screen Tests', () {
    testWidgets('App initializes and renders ReaderWorkbenchScreen with pure reader chrome', (tester) async {
      await tester.pumpWidget(const AIReaderApp());
      await tester.pumpAndSettle();

      expect(find.textContaining('分布式系统高可靠存储与认知解析'), findsWidgets);
      expect(find.textContaining('聚焦 (Cmd+D)'), findsOneWidget);

      // 验证返回书库按钮存在
      expect(find.byTooltip('返回书库 (文件管理)'), findsOneWidget);
    });

    testWidgets('Transitions between Pure Reader and LibraryScreen seamlessly', (tester) async {
      await tester.pumpWidget(const AIReaderApp());
      await tester.pumpAndSettle();

      // 点击返回书库按钮
      await tester.tap(find.byTooltip('返回书库 (文件管理)'));
      await tester.pumpAndSettle();

      // 验证进入独立书库模式
      expect(find.text('AI Reader 书库'), findsOneWidget);
      expect(find.text('导入文档'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget); // 搜索框
    });
  });
}
