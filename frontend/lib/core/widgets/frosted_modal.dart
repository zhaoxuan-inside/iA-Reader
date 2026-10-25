import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/reader_theme.dart';

/// 毛玻璃模态层 (FrostedModal)
///
/// 设计语言（DESIGN.md §4.3）：
/// - 弹窗外内容整屏高斯模糊（σ≈14）并轻度压暗；
/// - 面板内容完全不透明，阅读性优先；
/// - 面板边界无描边无硬阴影，以多层同色羽化光晕融入模糊背景，柔和过渡；
/// - 点击弹窗外任意区域关闭。
class FrostedModal extends StatelessWidget {
  final Widget child;
  final double width;
  final double maxHeight;
  final VoidCallback onDismiss;

  const FrostedModal({
    super.key,
    required this.child,
    required this.width,
    required this.onDismiss,
    this.maxHeight = 640.0,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onDismiss,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: ReaderTheme.drawerSlideDuration,
        curve: Curves.easeOutCubic,
        builder: (context, t, _) {
          return BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 14.0 * t, sigmaY: 14.0 * t),
            child: Container(
              color: isDark
                  ? Colors.black.withValues(alpha: 0.18 * t)
                  : Colors.black.withValues(alpha: 0.05 * t),
              alignment: Alignment.center,
              // 面板：多层同色光晕羽化边界，无描边硬线
              child: Opacity(
                opacity: t,
                child: Transform.scale(
                  scale: 0.96 + 0.04 * t,
                  child: Container(
                    width: width,
                    constraints: BoxConstraints(maxHeight: maxHeight),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18.0),
                      boxShadow: [
                        BoxShadow(
                          color: surface.withValues(alpha: 0.85),
                          blurRadius: 40.0,
                          spreadRadius: 12.0,
                        ),
                        BoxShadow(
                          color: surface.withValues(alpha: 0.50),
                          blurRadius: 90.0,
                          spreadRadius: 26.0,
                        ),
                        BoxShadow(
                          color: surface.withValues(alpha: 0.28),
                          blurRadius: 150.0,
                          spreadRadius: 40.0,
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18.0),
                      child: GestureDetector(
                        onTap: () {}, // 吞掉面板内点击，避免触发外部关闭
                        child: Material(color: surface, child: child),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
