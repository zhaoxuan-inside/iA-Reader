import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/main.dart';

/// 顶栏隐退/唤出回归测试（修复：悬停抖动）
///
/// 修复前：指针纯位置接近顶缘（dy<48）即唤出顶栏，与「下滚隐退」互相触发——
/// 阅读时指针停在顶栏附近，每次下滚隐退后指针微动又唤出，形成持续抖动。
/// 修复后：唤出需指针明确向上移动（delta.dy < -1.0）。
void main() {
  testWidgets('顶栏唤出需要明确向上移动意图，指针微动不再唤出', (tester) async {
    // 较矮视口保证正文内容可滚动（拖拽量按 maxScrollExtent 动态取值，避免过冲回弹）
    tester.view.physicalSize = const Size(1440, 500);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle(const Duration(milliseconds: 300));

    double headerHeight() =>
        tester.getSize(find.byType(AnimatedContainer).first).height;

    final listFinder = find.byType(ListView).first;
    // 主阅读列表的 Scrollable 在树序中最先出现（SelectableText 内部 Scrollable 为其后代）
    ScrollPosition position() =>
        tester.state<ScrollableState>(find.byType(Scrollable).first).position;

    // 初始状态：顶栏可见
    expect(headerHeight(), 44.0);
    expect(position().maxScrollExtent, greaterThan(60),
        reason: '测试前置：文档内容应可滚动');

    // 下滚阅读 → 顶栏隐退（拖 0.7 倍可滚距离，不触底过冲）
    await tester.drag(listFinder, Offset(0, -position().maxScrollExtent * 0.7));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
    expect(headerHeight(), 0.0, reason: '下滚后顶栏应隐退');

    // 指针悬停到顶缘（首次落点，无向上位移）→ 不应唤出
    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: const Offset(300, 40));
    addTearDown(gesture.removePointer);
    await tester.pumpAndSettle(const Duration(milliseconds: 100));
    expect(headerHeight(), 0.0, reason: '指针静止落在顶缘不应唤出顶栏');

    // 指针微动（向下 / 向上不足 1px 的漂移）→ 均不应唤出
    await gesture.moveTo(const Offset(300.5, 40.5));
    await tester.pumpAndSettle(const Duration(milliseconds: 100));
    expect(headerHeight(), 0.0, reason: '向下微动不应唤出顶栏');

    await gesture.moveTo(const Offset(301, 39.8));
    await tester.pumpAndSettle(const Duration(milliseconds: 100));
    expect(headerHeight(), 0.0, reason: '向上微漂（<1px）不应唤出顶栏');

    // 明确向上移动（阅读中把鼠标推向顶缘）→ 唤出
    await gesture.moveTo(const Offset(301, 24));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
    expect(headerHeight(), 44.0, reason: '明确向上移动应唤出顶栏');

    // 再次下滚 → 隐退；随后上滚 → 唤出（滚动方向控制不受影响）
    await tester.drag(listFinder, Offset(0, -position().maxScrollExtent * 0.3));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
    expect(headerHeight(), 0.0, reason: '下滚应再次隐退顶栏');

    await tester.drag(listFinder, Offset(0, position().maxScrollExtent * 0.5));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
    expect(headerHeight(), 44.0, reason: '上滚应唤出顶栏');
  });
}
