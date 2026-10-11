import 'package:flutter/services.dart';

/// 窗口控制通道：应用内顶栏为唯一标题栏时驱动原生窗口行为。
/// Linux runner 侧实现（my_application.cc）；其他平台/测试环境调用静默失败。
class WindowChannel {
  static const MethodChannel _channel = MethodChannel('ai.reader/window');

  static Future<void> minimize() async {
    try {
      await _channel.invokeMethod('minimize');
    } on PlatformException catch (_) {} on MissingPluginException catch (_) {}
  }

  /// 返回切换后的最大化状态
  static Future<bool> toggleMaximize() async {
    try {
      return await _channel.invokeMethod<bool>('toggleMaximize') ?? false;
    } on PlatformException catch (_) {
      return false;
    } on MissingPluginException catch (_) {
      return false;
    }
  }

  static Future<void> close() async {
    try {
      await _channel.invokeMethod('close');
    } on PlatformException catch (_) {} on MissingPluginException catch (_) {}
  }

  /// 拖动窗口：须在指针按住的拖拽手势中调用（Wayland 要求活跃按键 serial）
  static Future<void> beginDrag() async {
    try {
      await _channel.invokeMethod('beginDrag');
    } on PlatformException catch (_) {} on MissingPluginException catch (_) {}
  }
}
