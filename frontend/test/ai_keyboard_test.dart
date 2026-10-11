// AI 键盘测试（task_14）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/ai_keyboard/domain/ai_target_resolver.dart';
import 'package:ai_reader_frontend/features/ai_keyboard/presentation/ai_keyboard_panel.dart';
import 'package:ai_reader_frontend/features/selection_pill/presentation/floating_action_pill.dart';

void main() {
  group('AI 作用域解析纯函数', () {
    test('有划词选区 → 作用域为选区', () {
      final target = resolveAiTarget(
        selectionText: '预写式日志保证原子性',
        activeParagraphId: 'p2',
        paragraphTexts: const {'p1': '第一段', 'p2': '第二段内容'},
      );
      expect(target.isFromSelection, isTrue);
      expect(target.paragraphId, 'p2');
      expect(target.text, '预写式日志保证原子性');
    });

    test('无选区 → 回退聚焦段落全文', () {
      final target = resolveAiTarget(
        selectionText: null,
        activeParagraphId: 'p2',
        paragraphTexts: const {'p1': '第一段', 'p2': '第二段内容'},
      );
      expect(target.isFromSelection, isFalse);
      expect(target.paragraphId, 'p2');
      expect(target.text, '第二段内容');
    });

    test('无选区无聚焦 → 回退首段', () {
      final target = resolveAiTarget(
        selectionText: '',
        activeParagraphId: null,
        paragraphTexts: const {'p1': '第一段', 'p2': '第二段内容'},
      );
      expect(target.paragraphId, 'p1');
      expect(target.text, '第一段');
    });

    test('空文档 → 空目标', () {
      final target = resolveAiTarget(
        selectionText: null,
        activeParagraphId: null,
        paragraphTexts: const {},
      );
      expect(target.paragraphId, isNull);
      expect(target.text, isEmpty);
    });
  });

  group('AI 键盘面板', () {
    testWidgets('渲染四模板 + 伴读入口 + 作用域提示', (tester) async {
      CognitiveTemplateType? chosen;
      var companionRequested = false;

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Stack(children: [
            AiKeyboardPanel(
              targetHint: '作用域：选区「预写式日志」',
              onTemplateSelected: (t) => chosen = t,
              onOpenCompanion: () => companionRequested = true,
              onClose: () {},
            ),
          ]),
        ),
      ));

      expect(find.text('AI 键盘'), findsOneWidget);
      expect(find.text('作用域：选区「预写式日志」'), findsOneWidget);
      for (final label in ['通俗', '逻辑', '批判', '术语']) {
        expect(find.text(label), findsOneWidget, reason: label);
      }
      expect(find.text('认知伴读'), findsOneWidget);

      await tester.tap(find.text('逻辑'));
      expect(chosen, CognitiveTemplateType.logic);

      await tester.tap(find.text('认知伴读'));
      expect(companionRequested, isTrue);
    });
  });
}
