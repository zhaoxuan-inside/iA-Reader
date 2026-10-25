// integration_test/rust_engine_app_test.dart
// GUI 层端到端：真实 libreader_core.so 驱动真实应用界面
//
// 与 test/ 下全部走 mock 通道的 widget 测试互补，补上最后一环：
// "编译出的应用加载真引擎并渲染真书"。
//
// 运行方式（需先 cargo build --release 与 flutter build linux 工具链）：
//   export AI_READER_LIB=$PWD/backend/target/release/libreader_core.so
//   export AI_READER_HOME=$(mktemp -d)          # 隔离真实用户数据
//   export no_proxy=127.0.0.1,localhost          # 代理会劫持 tester 本地请求
//   flutter test integration_test/rust_engine_app_test.dart -d linux
//
// 契约：AI_READER_LIB 注入路径优先于 FLUTTER_TEST 强制 mock（reader_engine_bridge.dart）。

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:ai_reader_frontend/core/ffi/reader_engine_bridge.dart';
import 'package:ai_reader_frontend/main.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  final libPath = Platform.environment['AI_READER_LIB'] ?? '';
  final hasRealLib = libPath.isNotEmpty && File(libPath).existsSync();

  testWidgets('真引擎绑定 + 真实数据旅程（书库 → 工作台渲染）', (tester) async {
    expect(
      hasRealLib,
      isTrue,
      reason: 'AI_READER_LIB 未指向有效动态库，GUI e2e 无法直连真引擎（见文件头注释）',
    );

    // 工厂单例：先创建的桥接实例会被 App initState 复用
    final bridge = ReaderEngineBridge();
    expect(bridge.usesMockEngine, isFalse,
        reason: 'AI_READER_LIB=$libPath 注入未生效，仍运行在 mock 通道');

    // 旅程种子：向隔离 AI_READER_HOME 导入一篇两章节真书（标题取文件名词干）
    final sample = File(
        '${Directory.systemTemp.path}/gui_e2e_real_engine_sample.md');
    sample.writeAsStringSync(
      '# 第 1 章 预写式日志\n\n'
      '预写式日志是保证事务原子性与持久性的关键机制。\n\n'
      '# 第 2 章 快照隔离\n\n'
      '快照隔离让读取者绝不阻塞写入者。\n',
      encoding: utf8,
    );
    const bookTitle = 'gui_e2e_real_engine_sample';

    final parse = await bridge.invoke('book.parse', {'file_path': sample.path});
    expect(parse.isSuccess, isTrue, reason: '真引擎导入失败: ${parse.message}');
    final bookId = parse.data['id'] as int;

    // 真实书库数据（引擎级前置断言）
    final list = await bridge.invoke('book.list', {});
    final books = (list.data['books'] as List).cast<Map>();
    expect(books.any((b) => b['id'] == bookId), isTrue);
    expect(books.firstWhere((b) => b['id'] == bookId)['sections_count'], 2);

    // 启动真实应用：默认进入工作台（initialBookId=1 = 刚导入的真书）
    await tester.pumpWidget(const AIReaderApp());
    await tester.pumpAndSettle(const Duration(seconds: 5));

    // 真书标题必须替换 mock 默认标题（doc.get 数据来自真引擎）
    expect(
      find.textContaining(bookTitle),
      findsWidgets,
      reason: '工作台应渲染真引擎返回的书名（mock 默认标题为'
          '「分布式系统高可靠存储与认知解析」）',
    );
    // 真书正文段落渲染
    expect(find.textContaining('预写式日志'), findsWidgets);
    expect(find.textContaining('快照隔离'), findsWidgets);

    // 返回书库：列表同样来自真引擎 doc.list
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new));
    await tester.pumpAndSettle(const Duration(seconds: 5));
    expect(find.text('AI Reader 书库'), findsOneWidget);
    expect(find.textContaining(bookTitle), findsWidgets,
        reason: '书库列表应展示真引擎 doc.list 返回的真书');
  });
}
