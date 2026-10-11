import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/main.dart';

/// 诊断测试：切到白天模式后真实渲染阅读界面，导出 golden PNG 并打印实际生效颜色，
/// 用于定位「白天模式字体未变成黑色导致看不到文字」的报告。
void main() {
  testWidgets('白天模式渲染抓帧与颜色诊断', (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // 切到白天模式（与用户操作一致：点击顶栏「切换日夜模式」）
    await tester.tap(find.byTooltip('切换日夜模式'));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    final theme = Theme.of(tester.element(find.byType(MaterialApp)));
    // ignore: avoid_print
    print('brightness=${theme.brightness}');
    // ignore: avoid_print
    print('scaffoldBg=${theme.scaffoldBackgroundColor}');
    // ignore: avoid_print
    print('bodyLarge.color=${theme.textTheme.bodyLarge!.color}');
    // ignore: avoid_print
    print('bodyMedium.color=${theme.textTheme.bodyMedium!.color}');

    // 阅读区实际渲染的正文与继承样式（标题走 DefaultTextStyle 继承链）
    final selectable = find.byType(SelectableText);
    // ignore: avoid_print
    print('selectableTexts=${selectable.evaluate().length}');
    if (selectable.evaluate().isNotEmpty) {
      final el = selectable.evaluate().first;
      final widget = el.widget as SelectableText;
      // ignore: avoid_print
      print('selectable.style.color=${widget.style?.color}');
      // ignore: avoid_print
      print('selectable DefaultTextStyle.color=${DefaultTextStyle.of(el).style.color}');
    }

    // 大标题（无显式颜色，走继承）
    final titleFinder = find.text('分布式系统高可靠存储与认知解析').last;
    if (titleFinder.evaluate().isNotEmpty) {
      final el = titleFinder.evaluate().first;
      final dts = DefaultTextStyle.of(el);
      // ignore: avoid_print
      print('bookTitle DefaultTextStyle.color=${dts.style.color} fontSize=${dts.style.fontSize}');
      final style = (el.widget as Text).style;
      // ignore: avoid_print
      print('bookTitle explicitStyle.color=${style?.color}');
    }

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/light_mode_reader.png'),
    );
  });

  testWidgets('白天模式书库渲染抓帧', (tester) async {
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // 返回书库
    await tester.tap(find.byTooltip('返回书库 (文件管理)'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));

    // 切到白天模式
    await tester.tap(find.byTooltip('切换日夜模式'));
    await tester.pumpAndSettle(const Duration(milliseconds: 300));

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/light_mode_library.png'),
    );
  });
}
