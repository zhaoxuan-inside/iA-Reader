import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/core/widgets/frosted_modal.dart';
import 'package:ai_reader_frontend/features/selection_pill/presentation/floating_action_pill.dart';
import 'package:ai_reader_frontend/main.dart';

/// 毛玻璃弹窗与划词胶囊交互回归测试（task_11 UI 交互改造）
void main() {
  Future<void> pumpDesktopApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle();
  }

  testWidgets('目录/导图以毛玻璃弹窗打开，点击弹窗外关闭', (tester) async {
    await pumpDesktopApp(tester);

    await tester.tap(find.byTooltip('文章罗盘/目录 (Cmd+\\)'));
    await tester.pumpAndSettle();

    expect(find.text('文章导航'), findsOneWidget, reason: '目录弹窗应打开');
    expect(find.byType(FrostedModal), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget, reason: '应有背景高斯模糊');

    // 点击弹窗外区域 → 关闭
    await tester.tapAt(const Offset(40, 500));
    await tester.pumpAndSettle();
    expect(find.text('文章导航'), findsNothing, reason: '点击弹窗外应关闭弹窗');
  });

  testWidgets('AI 认知伴读以毛玻璃弹窗打开，点击弹窗外关闭', (tester) async {
    await pumpDesktopApp(tester);

    await tester.tap(find.byTooltip('AI 认知伴读'));
    await tester.pumpAndSettle();

    expect(find.text('认知洞察'), findsOneWidget, reason: '伴读弹窗应打开');
    expect(find.byType(FrostedModal), findsOneWidget);

    await tester.tapAt(const Offset(40, 500));
    await tester.pumpAndSettle();
    expect(find.text('认知洞察'), findsNothing, reason: '点击弹窗外应关闭弹窗');
  });

  testWidgets('划词胶囊锚定在选中文本附近，点击其他区域自动消失', (tester) async {
    await pumpDesktopApp(tester);

    // 长按后拖拽划词（确定性构造非折叠选区）→ 胶囊出现
    final paragraphFinder = find.textContaining('现代分布式系统').first;
    expect(paragraphFinder, findsOneWidget);
    final paraRect = tester.getRect(paragraphFinder);
    final gesture = await tester.startGesture(paraRect.center - const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 700)); // 越过长按阈值
    await gesture.moveBy(const Offset(160, 0));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();

    expect(find.byType(FloatingActionPill), findsOneWidget, reason: '划词后应出现功能胶囊');

    // 胶囊应锚定选区附近（垂直方向贴近该段落），而非固定位置
    final pillRect = tester.getRect(find.byType(FloatingActionPill));
    expect(pillRect.bottom, greaterThanOrEqualTo(paraRect.top - 80),
        reason: '胶囊应出现在段落上方不远处');
    expect(pillRect.top, lessThanOrEqualTo(paraRect.bottom + 40),
        reason: '胶囊不应远离所选段落');

    // 点击其他区域 → 胶囊自动消失
    await tester.tapAt(const Offset(60, 560));
    await tester.pumpAndSettle();
    expect(find.byType(FloatingActionPill), findsNothing, reason: '点击其他区域胶囊应消失');
  });
}
