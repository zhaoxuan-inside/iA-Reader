// test/library_delete_test.dart
// 书库删除文档流程（FEAT-001 书库管理）：确认后从列表移除，取消则保留。
// mock 通道（FLUTTER_TEST）下 doc.list/book.delete 均由进程内 mock 引擎应答。

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';
import 'package:ai_reader_frontend/features/library/presentation/library_screen.dart';

void main() {
  testWidgets('删除文档：取消保留 / 确认后从书库移除', (tester) async {
    final bridge = ReaderEngineBridge();
    bridge.resetMockStateForTest();

    await tester.pumpWidget(MaterialApp(
      home: LibraryScreen(
        bridge: bridge,
        onOpenBook: (_) {},
        onToggleTheme: () {},
        isDarkMode: false,
      ),
    ));
    await tester.pumpAndSettle();

    // mock 书库初始两本
    expect(find.textContaining('分布式系统高可靠存储与认知解析'), findsOneWidget);
    expect(find.textContaining('深度学习与认知推理实战指南'), findsOneWidget);

    // 取消路径：删除确认框弹出后取消，两本仍在
    await tester.tap(find.byTooltip('删除文档').first);
    await tester.pumpAndSettle();
    expect(find.text('删除文档'), findsOneWidget, reason: '确认框应弹出');
    await tester.tap(find.widgetWithText(TextButton, '取消'));
    await tester.pumpAndSettle();
    expect(find.textContaining('分布式系统高可靠存储与认知解析'), findsOneWidget,
        reason: '取消后书不应被删除');

    // 确认路径：删除第一本，仅剩第二本
    await tester.tap(find.byTooltip('删除文档').first);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, '删除'));
    await tester.pumpAndSettle();
    expect(find.textContaining('分布式系统高可靠存储与认知解析'), findsNothing,
        reason: '确认后该书应从列表移除');
    expect(find.textContaining('深度学习与认知推理实战指南'), findsOneWidget);
  });
}
