// test/app_settings_test.dart
// 应用配置持久化（验收项：黑暗/白天模式跨重启保留）：
// 1. 启动恢复:mock settings 里的 theme_mode/last_book_id 决定首屏
// 2. 切换即存:主题切换与打开书籍触发 settings.save

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';
import 'package:ai_reader_frontend/main.dart';

void main() {
  testWidgets('启动恢复:theme_mode=light → 应用以亮色启动', (tester) async {
    final bridge = ReaderEngineBridge();
    bridge.resetMockStateForTest();
    await bridge.invoke('settings.save', {
      'settings': {'theme_mode': 'light'},
    });

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle();

    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.light, reason: '启动应恢复为亮色模式');
  });

  testWidgets('切换即存:点击切换主题 → settings.save 落库 theme_mode', (tester) async {
    final bridge = ReaderEngineBridge();
    bridge.resetMockStateForTest();

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle();
    var app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.dark, reason: '无记录时默认暗色');

    // 顶栏日夜切换按钮:暗色态显示 light_mode 图标(点击切到亮色)
    await tester.tap(find.byIcon(Icons.light_mode_outlined).first);
    await tester.pumpAndSettle();

    app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.light, reason: '点击后应切为亮色');

    // 持久化断言:mock settings 中 theme_mode 已写入 light
    final res = await bridge.invoke('settings.get', {});
    expect(res.data['settings']['theme_mode'], 'light',
        reason: '切换必须落库,否则重启即丢');
  });

  testWidgets('上次书目:last_book_id 指向已删除的书 → 回书库页', (tester) async {
    final bridge = ReaderEngineBridge();
    bridge.resetMockStateForTest();
    // mock 书库默认含 id 1/2;42 不存在
    await bridge.invoke('settings.save', {
      'settings': {'last_book_id': 42},
    });

    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle();

    expect(find.text('AI Reader 书库'), findsOneWidget,
        reason: 'last_book_id 失效应回书库而非空白阅读页');
  });
}
