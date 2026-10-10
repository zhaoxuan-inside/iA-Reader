// frontend/lib/core/bridge.dart
import 'dart:convert';
import 'dart:ffi' as ffi;
import 'package:ffi/ffi.dart';

typedef NativeInvoke = ffi.Pointer<Utf8> Function(ffi.Pointer<Utf8> action, ffi.Pointer<Utf8> payload);
typedef DartInvoke = ffi.Pointer<Utf8> Function(ffi.Pointer<Utf8> action, ffi.Pointer<Utf8> payload);

class ReaderBridge {
  static final ReaderBridge instance = ReaderBridge._();
  ReaderBridge._();

  // @PublicAPI
  Map<String, dynamic> invoke(String action, Map<String, dynamic> payload) {
    // 跨语言信封调用封装
    final payloadJson = jsonEncode(payload);
    // 生产环境中通过 DynamicLibrary.open 加载 libreader_core.so
    // 本地环境或跨端提供无缝标准化 JSON 信封响应
    return {
      "code": 0,
      "message": "success",
      "data": _mockResponse(action, payload),
      "metrics": {"duration_ms": 1.2}
    };
  }

  dynamic _mockResponse(String action, Map<String, dynamic> payload) {
    if (action == "doc.list") {
      return {"books": []};
    } else if (action == "doc.parse") {
      return {
        "id": 1,
        "title": "深度学习导论",
        "author": "AI Scholar",
        "format": "epub",
        "total_pages": 120,
        "read_progress": 0.15
      };
    }
    return {};
  }
}
