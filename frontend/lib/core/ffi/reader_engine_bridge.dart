import 'dart:convert';
import 'dart:ffi' as ffi;
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

/// C-ABI 原生 FFI 桥接客户端
class ReaderEngineBridge {
  static ReaderEngineBridge? _instance;
  final ReaderInvokeDart? _nativeInvoke;

  ReaderEngineBridge._({ReaderInvokeDart? nativeInvoke})
      : _nativeInvoke = nativeInvoke;

  factory ReaderEngineBridge({ReaderInvokeDart? nativeInvoke}) {
    _instance ??= ReaderEngineBridge._(nativeInvoke: nativeInvoke);
    return _instance!;
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
        final Map<String, dynamic> parsed = jsonDecode(resultStr);
        return InvokeEnvelope.fromJson(parsed);
      } finally {
        malloc.free(actionPtr);
        malloc.free(payloadPtr);
      }
    }

    // 离线/开发环境模拟回退 (Mock Fallback)
    return _mockFallback(action, payload);
  }

  InvokeEnvelope _mockFallback(String action, Map<String, dynamic> payload) {
    final now = DateTime.now().millisecondsSinceEpoch;
    if (action == 'ai.companion_ask') {
      final tpl = payload['template'] ?? 'general';
      final text = payload['selected_text'] ?? '';
      return InvokeEnvelope(
        code: 0,
        message: 'Success (Mock Fallback)',
        data: {
          'analysis': '【$tpl 认知分析】针对选区：“$text”：\n\n'
              '1. 核心因果链：本段论点阐述了系统的关键状态流转机制。\n'
              '2. 关键洞察：锁竞争与资源消耗在当前架构下被完全隔离。\n'
              '3. 延伸思考：请关注边界负载与异常重试策略。',
          'template': tpl,
          'token_count': 128,
        },
        metrics: {'duration_ms': 12, 'timestamp': now},
      );
    } else if (action == 'annotation.save') {
      return InvokeEnvelope(
        code: 0,
        message: 'Saved',
        data: {'annotation_id': 'annot_mock_${now}', 'status': 'persisted'},
        metrics: {'duration_ms': 3, 'timestamp': now},
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
