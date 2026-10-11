// 窗口控制自绘图标测试（task_12 D3/D4：最小化/最大化可见性）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/core/widgets/window_controls.dart';

void main() {
  testWidgets('三个窗口控制按钮齐备且为自绘 CustomPaint（无 Material Icon）', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: Center(child: WindowControls(color: Colors.grey))),
    ));

    expect(find.byTooltip('最小化'), findsOneWidget);
    expect(find.byTooltip('最大化窗口'), findsOneWidget);
    expect(find.byTooltip('关闭'), findsOneWidget);

    // 自绘线性图标：不依赖 Material 图标字体
    final iconsInControls = find.descendant(
      of: find.byType(WindowControls),
      matching: find.byType(Icon),
    );
    expect(iconsInControls, findsNothing);
    expect(find.descendant(of: find.byType(WindowControls), matching: find.byType(CustomPaint)),
        findsAtLeastNWidgets(3));
  });

  testWidgets('点击最大化/还原按钮切换共享状态且不崩溃（测试环境通道降级）', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: Center(child: WindowControls(color: Colors.grey))),
    ));

    await tester.tap(find.byTooltip('最大化窗口'));
    await tester.pump();
    // 测试环境无原生通道，toggleMaximize 降级返回 false，不应抛出
    expect(windowMaximized.value, isFalse);

    await tester.tap(find.byTooltip('最小化'));
    await tester.tap(find.byTooltip('关闭'));
    await tester.pump();
  });
}
