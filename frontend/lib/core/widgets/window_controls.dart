import 'package:flutter/material.dart';

import '../window/window_channel.dart';

/// 最大化状态（跨组件共享：顶栏双击与窗口控制按钮同一状态源）
final ValueNotifier<bool> windowMaximized = ValueNotifier(false);

/// 切换窗口最大化并同步状态
Future<void> toggleWindowMaximize() async {
  windowMaximized.value = await WindowChannel.toggleMaximize();
}

/// 无边框窗口的应用内窗口控制（最小化/最大化/关闭）。
/// 图标用 CustomPaint 自绘细线（task_12 D3/D4）：Material 图标字体在小尺寸下
/// 横线过细（horizontal_rule）与方框糊化（fullscreen）导致用户不可辨识；
/// 自绘保证任何渲染栈下线宽与对比度可控，亦贴合 iA 纯线性语言。
class WindowControls extends StatelessWidget {
  final Color color;
  final double iconSize;

  const WindowControls({
    super.key,
    required this.color,
    this.iconSize = 14.0,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: '最小化',
          icon: _LineIcon(
            painter: _MinimizeIconPainter(color),
            size: iconSize,
          ),
          onPressed: WindowChannel.minimize,
        ),
        ValueListenableBuilder<bool>(
          valueListenable: windowMaximized,
          builder: (context, isMaximized, _) {
            return IconButton(
              visualDensity: VisualDensity.compact,
              tooltip: isMaximized ? '还原窗口' : '最大化窗口',
              icon: _LineIcon(
                painter: isMaximized
                    ? _RestoreIconPainter(color)
                    : _MaximizeIconPainter(color),
                size: iconSize,
              ),
              onPressed: toggleWindowMaximize,
            );
          },
        ),
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: '关闭',
          icon: _LineIcon(
            painter: _CloseIconPainter(color),
            size: iconSize,
          ),
          onPressed: WindowChannel.close,
        ),
      ],
    );
  }
}

/// 线性图标容器：固定画布 + CustomPaint，笔画 1.4 逻辑像素
class _LineIcon extends StatelessWidget {
  final CustomPainter painter;
  final double size;

  const _LineIcon({required this.painter, required this.size});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: painter),
    );
  }
}

class _MinimizeIconPainter extends CustomPainter {
  final Color color;
  _MinimizeIconPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.4
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    canvas.drawLine(
      Offset(size.width * 0.15, size.height * 0.85),
      Offset(size.width * 0.85, size.height * 0.85),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _MinimizeIconPainter old) => old.color != color;
}

class _MaximizeIconPainter extends CustomPainter {
  final Color color;
  _MaximizeIconPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke;
    canvas.drawRect(
      Rect.fromLTWH(size.width * 0.12, size.height * 0.12,
          size.width * 0.76, size.height * 0.76),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _MaximizeIconPainter old) => old.color != color;
}

class _RestoreIconPainter extends CustomPainter {
  final Color color;
  _RestoreIconPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke;
    // 后方方框只画上/右两边（经典还原图标，避免交叠线糊成一团）
    final backPath = Path()
      ..moveTo(size.width * 0.30, size.height * 0.10)
      ..lineTo(size.width * 0.90, size.height * 0.10)
      ..lineTo(size.width * 0.90, size.height * 0.70);
    canvas.drawPath(backPath, paint);
    // 前方完整方框（左下）
    canvas.drawRect(
      Rect.fromLTWH(size.width * 0.10, size.height * 0.30,
          size.width * 0.62, size.height * 0.62),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _RestoreIconPainter old) => old.color != color;
}

class _CloseIconPainter extends CustomPainter {
  final Color color;
  _CloseIconPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.4
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    canvas.drawLine(
      Offset(size.width * 0.18, size.height * 0.18),
      Offset(size.width * 0.82, size.height * 0.82),
      paint,
    );
    canvas.drawLine(
      Offset(size.width * 0.82, size.height * 0.18),
      Offset(size.width * 0.18, size.height * 0.82),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _CloseIconPainter old) => old.color != color;
}
