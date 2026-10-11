import 'dart:ui' show Offset, Size;

/// 划词胶囊锚定度量与纯函数（task_12 D1：胶囊跟随鼠标位置）。
/// 纯函数无 BuildContext 依赖，便于单测与两端复用。
class PillAnchorMetrics {
  static const double pillWidth = 300.0; // 6 按钮（含「标注」）后的胶囊宽度
  static const double pillHeight = 38.0;
  static const double margin = 16.0;
  static const double minTop = 56.0; // 顶栏 44px + 呼吸 12px
  static const double pointerGap = 12.0; // 胶囊底边与指针的间隙
}

/// 胶囊锚定于鼠标指针位置：水平居中于指针、垂直悬于指针上方，
/// 越界时 clamp 进窗口可视范围。
Offset anchorPillAtPointer(
  Offset pointer,
  Size screen, {
  double pillWidth = PillAnchorMetrics.pillWidth,
  double pillHeight = PillAnchorMetrics.pillHeight,
}) {
  double dx = pointer.dx - pillWidth / 2.0;
  double dy = pointer.dy - pillHeight - PillAnchorMetrics.pointerGap;

  final maxDx = (screen.width - pillWidth - PillAnchorMetrics.margin)
      .clamp(PillAnchorMetrics.margin, double.infinity);
  dx = dx.clamp(PillAnchorMetrics.margin, maxDx);

  // 指针过低时胶囊翻转夹紧到窗口底部安全区，避免溢出
  if (dy + pillHeight > screen.height - PillAnchorMetrics.margin) {
    dy = screen.height - pillHeight - PillAnchorMetrics.margin;
  }
  dy = dy.clamp(PillAnchorMetrics.minTop, double.infinity);
  return Offset(dx, dy);
}
