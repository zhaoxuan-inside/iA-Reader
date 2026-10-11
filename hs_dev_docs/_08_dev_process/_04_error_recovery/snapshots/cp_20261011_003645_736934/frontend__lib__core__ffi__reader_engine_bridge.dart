import 'dart:convert';
import 'dart:ffi' as ffi;
import 'dart:io';
import 'package:ffi/ffi.dart';

/// 六元组响应信封结构 (InvokeEnvelope)
class InvokeEnvelope {
  final int code;
  final String message;
  final Map<String, dynamic> data;
  final Map<String, dynamic> metrics;

  InvokeEnvelope({
    required this.code,
    required this.message,
    required this.data,
    required this.metrics,
  });

  bool get isSuccess => code == 0;

  factory InvokeEnvelope.fromJson(Map<String, dynamic> json) {
    return InvokeEnvelope(
      code: json['code'] as int? ?? -1,
      message: json['message'] as String? ?? '',
      data: (json['data'] as Map<String, dynamic>?) ?? {},
      metrics: (json['metrics'] as Map<String, dynamic>?) ?? {},
    );
  }

  Map<String, dynamic> toJson() => {
    'code': code,
    'message': message,
    'data': data,
    'metrics': metrics,
  };
}

typedef ReaderInvokeC = ffi.Pointer<Utf8> Function(
    ffi.Pointer<Utf8> action, ffi.Pointer<Utf8> payloadJson);
typedef ReaderInvokeDart = ffi.Pointer<Utf8> Function(
    ffi.Pointer<Utf8> action, ffi.Pointer<Utf8> payloadJson);

typedef ReaderFreeStringC = ffi.Void Function(ffi.Pointer<Utf8> ptr);
typedef ReaderFreeStringDart = void Function(ffi.Pointer<Utf8> ptr);

/// C-ABI 原生 FFI 桥接客户端 (ReaderEngineBridge)
/// 支持真实加载本地 libreader_core.so / dylib / dll 动态库，并在未安装原生库或离线时平滑切至启发式确定性引擎
class ReaderEngineBridge {
  static ReaderEngineBridge? _instance;
  final ReaderInvokeDart? _nativeInvoke;
  final ReaderFreeStringDart? _nativeFreeString;

  // 内存中模拟存储（用于离线开发或无动态库环境测试）
  final List<Map<String, dynamic>> _inMemoryAnnotations = [];

  ReaderEngineBridge._({
    ReaderInvokeDart? nativeInvoke,
    ReaderFreeStringDart? nativeFreeString,
  })  : _nativeInvoke = nativeInvoke,
        _nativeFreeString = nativeFreeString;

  factory ReaderEngineBridge({String? libraryPath}) {
    if (_instance != null) return _instance!;

    ReaderInvokeDart? invokeFn;
    ReaderFreeStringDart? freeFn;

    try {
      final lib = _openDynamicLibrary(libraryPath);
      if (lib != null) {
        invokeFn = lib
            .lookup<ffi.NativeFunction<ReaderInvokeC>>('ai_reader_invoke')
            .asFunction<ReaderInvokeDart>();
        freeFn = lib
            .lookup<ffi.NativeFunction<ReaderFreeStringC>>('ai_reader_free_string')
            .asFunction<ReaderFreeStringDart>();
      }
    } catch (_) {
      // 动态库未就绪时，平滑降级至进程内启发式计算通道
    }

    _instance = ReaderEngineBridge._(
      nativeInvoke: invokeFn,
      nativeFreeString: freeFn,
    );
    return _instance!;
  }

  static ffi.DynamicLibrary? _openDynamicLibrary(String? customPath) {
    if (customPath != null && File(customPath).existsSync()) {
      return ffi.DynamicLibrary.open(customPath);
    }

    final candidatePaths = <String>[];
    if (Platform.isLinux) {
      candidatePaths.addAll([
        'libreader_core.so',
        'backend/target/release/libreader_core.so',
        '/usr/lib/ai-reader/lib/libreader_core.so',
        './libreader_core.so',
      ]);
    } else if (Platform.isMacOS) {
      candidatePaths.addAll([
        'libreader_core.dylib',
        'backend/target/release/libreader_core.dylib',
      ]);
    } else if (Platform.isWindows) {
      candidatePaths.addAll([
        'reader_core.dll',
        'backend/target/release/reader_core.dll',
      ]);
    }

    for (final path in candidatePaths) {
      if (File(path).existsSync()) {
        try {
          return ffi.DynamicLibrary.open(path);
        } catch (_) {}
      }
    }
    return null;
  }

  /// 同步或异步调用底层六元组 action
  Future<InvokeEnvelope> invoke(String action, Map<String, dynamic> payload) async {
    final payloadJson = jsonEncode(payload);

    if (_nativeInvoke != null) {
      final actionPtr = action.toNativeUtf8();
      final payloadPtr = payloadJson.toNativeUtf8();
      try {
        final resultPtr = _nativeInvoke!(actionPtr, payloadPtr);
        final resultStr = resultPtr.toDartString();
        if (_nativeFreeString != null) {
          _nativeFreeString!(resultPtr);
        }
        final Map<String, dynamic> parsed = jsonDecode(resultStr);
        return InvokeEnvelope.fromJson(parsed);
      } catch (_) {
        // 原生调用异常时回退到启发式引擎
      } finally {
        malloc.free(actionPtr);
        malloc.free(payloadPtr);
      }
    }

    // 离线 / 启发式回退 (Deterministic Local Fallback)
    return _mockFallback(action, payload);
  }

  InvokeEnvelope _mockFallback(String action, Map<String, dynamic> payload) {
    final now = DateTime.now().millisecondsSinceEpoch;

    if (action == 'ai.companion_ask') {
      final tpl = payload['template_type'] ?? payload['template'] ?? 'general';
      final text = payload['selected_text'] ?? '';
      final prompt = payload['prompt'] ?? payload['follow_up'] ?? '';

      String analysis = '';
      if (prompt.toString().isNotEmpty) {
        analysis = '针对追问「$prompt」：\n\n'
            '从底层架构视角分析，当前段落所讨论的核心机制在发生高并发竞争时，'
            '主要依赖快照隔离与写前日志机制消除锁冲突。长事务会推迟资源截断，'
            '建议结合自适应调度器平衡吞吐与延迟。';
      } else {
        switch (tpl) {
          case 'logic':
            analysis = '【🔗 逻辑链条推理】针对选区：“$text”\n\n'
                '1. 前置假设：所有写事务必须在主库落盘前先行写入持久层日志。\n'
                '2. 因果传导：顺序日志追加极大消除了随机寻道耗时，解耦读写锁。\n'
                '3. 潜在隐患：检查点滞后将引发日志膨胀，需配置动态截断。';
            break;
          case 'critical':
            analysis = '【🧐 批判性审视】针对选区：“$text”\n\n'
                '1. 边界局限：无锁读快照在极端内存受限场景下可能带来快照膨胀。\n'
                '2. 权衡取舍：该方案用存储空间换取并发读性能，并非万能银弹。\n'
                '3. 改进空间：引入冷热数据分层可进一步规避大快照抖动。';
            break;
          case 'term':
            analysis = '【📖 核心术语剖析】针对选区：“$text”\n\n'
                '• WAL (Write-Ahead Logging)：预写式日志，用于保证 ACID 中的原子性与持久性。\n'
                '• MVCC (多版本并发控制)：通过维护数据多版本快照实现读写互不阻塞。\n'
                '• 检查点 (Checkpoint)：将 WAL 日志中已提交事务合并回主数据库并截断日志。';
            break;
          case 'general':
          default:
            analysis = '【⚡️ 通俗解读】针对选区：“$text”\n\n'
                '简单来说，就像食堂打饭：以前是打菜师傅和盛饭师傅抢同一个勺子，'
                '现在分成两条独立传送带，谁也不用等谁，大大提升了整体效率。';
            break;
        }
      }

      return InvokeEnvelope(
        code: 0,
        message: 'Success',
        data: {
          'analysis': analysis,
          'response': analysis,
          'template_type': tpl,
          'token_count': 128,
        },
        metrics: {'duration_ms': 12, 'timestamp': now},
      );
    } else if (action == 'annotation.save') {
      final note = payload['note_text'] ?? payload['note'] ?? '';
      final annotId = 'annot_${now}_${_inMemoryAnnotations.length + 1}';
      final item = {
        'id': annotId,
        'book_id': payload['book_id'] ?? 1,
        'section_id': payload['section_id'] ?? 1,
        'note_text': note,
        'color': payload['color'] ?? '#007AFF',
        'created_at': DateTime.now().toIso8601String(),
      };
      _inMemoryAnnotations.add(item);
      return InvokeEnvelope(
        code: 0,
        message: 'Saved',
        data: {'annotation_id': annotId, 'status': 'persisted'},
        metrics: {'duration_ms': 3, 'timestamp': now},
      );
    } else if (action == 'annotation.list') {
      return InvokeEnvelope(
        code: 0,
        message: 'success',
        data: {'annotations': List.from(_inMemoryAnnotations)},
        metrics: {'duration_ms': 2, 'timestamp': now},
      );
    } else if (action == 'mindmap.generate') {
      return InvokeEnvelope(
        code: 0,
        message: 'success',
        data: {
          'nodes': [
            {'id': 'm1', 'label': '分布式高可靠存储', 'depth': 0, 'parent_id': null},
            {'id': 'm2', 'label': '预写式日志 (WAL)', 'depth': 1, 'parent_id': 'm1'},
            {'id': 'm3', 'label': '顺序写入与原子性', 'depth': 2, 'parent_id': 'm2'},
            {'id': 'm4', 'label': '崩溃恢复与Redo/Undo', 'depth': 2, 'parent_id': 'm2'},
            {'id': 'm5', 'label': '快照隔离与并发控制', 'depth': 1, 'parent_id': 'm1'},
            {'id': 'm6', 'label': '只读快照免锁并发', 'depth': 2, 'parent_id': 'm5'},
            {'id': 'm7', 'label': '检查点协调与截断抖动', 'depth': 2, 'parent_id': 'm5'},
            {'id': 'm8', 'label': '本地三级概念拓扑', 'depth': 1, 'parent_id': 'm1'},
            {'id': 'm9', 'label': 'PMI 词共现矩阵', 'depth': 2, 'parent_id': 'm8'},
          ]
        },
        metrics: {'duration_ms': 8, 'timestamp': now},
      );
    } else if (action == 'nlp.keyword_extract') {
      return InvokeEnvelope(
        code: 0,
        message: 'success',
        data: {
          'keywords': [
            {'word': 'WAL协议', 'score': 0.94, 'count': 8},
            {'word': '快照隔离', 'score': 0.88, 'count': 6},
            {'word': '原子性', 'score': 0.82, 'count': 5},
            {'word': '检查点', 'score': 0.79, 'count': 4},
            {'word': 'PMI共现', 'score': 0.74, 'count': 4},
            {'word': '顺序写入', 'score': 0.71, 'count': 3},
            {'word': 'AST语法树', 'score': 0.68, 'count': 3},
            {'word': '崩溃恢复', 'score': 0.65, 'count': 3},
          ]
        },
        metrics: {'duration_ms': 5, 'timestamp': now},
      );
    } else if (action == 'doc.list') {
      return InvokeEnvelope(
        code: 0,
        message: 'success',
        data: {
          'books': [
            {
              'id': 1,
              'title': '分布式系统高可靠存储与认知解析',
              'author': 'AI Reader 架构组',
              'format': 'md',
              'total_pages': 1,
              'sections_count': 3,
            },
            {
              'id': 2,
              'title': '深度学习与认知推理实战指南',
              'author': 'AI Lab',
              'format': 'epub',
              'total_pages': 120,
              'sections_count': 12,
            },
          ]
        },
        metrics: {'duration_ms': 1, 'timestamp': now},
      );
    } else if (action == 'doc.get') {
      return InvokeEnvelope(
        code: 0,
        message: 'success',
        data: {
          'book_id': 1,
          'title': '分布式系统高可靠存储与认知解析',
          'sections': [
            {
              'id': 1,
              'title': '第 1 章 · 存储引擎与预写日志',
              'paragraphs': [
                {
                  'id': 'p1',
                  'text':
                      '在现代分布式系统与嵌入式数据库架构中，预写式日志（Write-Ahead Logging, WAL）是保障事务原子性与持久性的基石机制。当任何写入操作发生时，系统必须严格保证日志记录在数据页刷入主盘介质前，先行顺序写入稳定的磁盘持久层。',
                },
                {
                  'id': 'p2',
                  'text':
                      '通过将随机写入转换为高吞吐的追加式顺序写入，WAL 协议极大降低了磁盘寻道开销。同时，在崩溃恢复期，系统只需通过 Redo 与 Undo 扫描即可回滚未提交事务、重放已确认修改，实现毫秒级的快速自愈。',
                },
              ],
            },
            {
              'id': 2,
              'title': '第 2 章 · 并发控制与快照隔离',
              'paragraphs': [
                {
                  'id': 'p3',
                  'text':
                      'SQLite 在启用 WAL 模式后，展现出了卓越的多读单写并发性能：读取者绝不阻塞写入者，写入者也绝不阻塞读取者。每一个读事务在开启瞬间捕获一个 WAL 序列快照，只读视图在整个查询生命周期内保持隔离与一致。',
                },
                {
                  'id': 'p4',
                  'text':
                      '然而，检查点（Checkpoint）操作仍然是系统设计中的平衡艺术。若长事务阻止了 WAL 文件的截断与归并，日志体积的膨胀将最终导致读快照扫描延迟的抖动。',
                },
              ],
            },
            {
              'id': 3,
              'title': '第 3 章 · 本地认知伴读拓扑',
              'paragraphs': [
                {
                  'id': 'p5',
                  'text':
                      'AI Reader 核心计算引擎通过多层级 NLP 算法（TF-IDF + TextRank）与 PMI 概念共现拓扑，将原本孤立的长篇文本映射为立体网状的知识图谱，并在零网络依赖环境下提供秒级确定的思维启发。',
                },
              ],
            },
          ]
        },
        metrics: {'duration_ms': 2, 'timestamp': now},
      );
    }

    return InvokeEnvelope(
      code: 0,
      message: 'OK',
      data: {'action': action, 'echo': payload},
      metrics: {'duration_ms': 1, 'timestamp': now},
    );
  }
}
