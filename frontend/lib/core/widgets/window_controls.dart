import 'package:flutter/material.dart';

import '../window/window_channel.dart';

/// 最大化状态（跨组件共享：顶栏双击与窗口控制按钮同一状态源）
final ValueNotifier<bool> windowMaximized = ValueNotifier(false);

/// 切换窗口最大化并同步状态
Future<void> toggleWindowMaximize() async {
  windowMaximized.value = await WindowChannel.toggleMaximize();
}

/// 无边框窗口的应用内窗口控制（最小化/最大化/关闭）
/// iA 语言：极简线性图标、次要色，置于应用内顶栏右端
class WindowControls extends StatelessWidget {
  final Color color;
  final double iconSize;

  const WindowControls({
    Key? key,
    required this.color,
    this.iconSize = 13.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: '最小化',
          icon: Icon(Icons.horizontal_rule, size: iconSize, color: color),
          onPressed: WindowChannel.minimize,
        ),
        ValueListenableBuilder<bool>(
          valueListenable: windowMaximized,
          builder: (context, isMaximized, _) {
            return IconButton(
              visualDensity: VisualDensity.compact,
              tooltip: isMaximized ? '还原窗口' : '最大化窗口',
              icon: Icon(
                isMaximized ? Icons.fullscreen_exit : Icons.fullscreen,
                size: iconSize + 2.0,
                color: color,
              ),
              onPressed: toggleWindowMaximize,
            );
          },
        ),
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: '关闭',
          icon: Icon(Icons.close, size: iconSize + 2.0, color: color),
          onPressed: WindowChannel.close,
        ),
      ],
    );
  }
}
