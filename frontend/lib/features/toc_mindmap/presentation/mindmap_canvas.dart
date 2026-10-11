import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../../core/theme/reader_theme.dart';
import 'toc_mindmap_drawer.dart';

/// 画布节点几何常量
const double kMindmapNodeWidth = 132.0;
const double kMindmapNodeHeight = 34.0;
const double kMindmapHGap = 44.0;
const double kMindmapVGap = 12.0;

/// 布局结果：节点左上角坐标 + 画布尺寸
class MindmapLayoutResult {
  final Map<String, Offset> positions;
  final Size canvasSize;

  const MindmapLayoutResult({required this.positions, required this.canvasSize});
}

/// tidy tree 布局（task_15 D1）：横向树——叶子按序占行、父 y=子均值、x=depth 步进。
/// 孤儿节点（父不存在）视作根；环引用只访问一次，不死循环。
MindmapLayoutResult layoutMindmapTree(
  List<MindmapNodeItem> nodes, {
  double nodeWidth = kMindmapNodeWidth,
  double nodeHeight = kMindmapNodeHeight,
  double hGap = kMindmapHGap,
  double vGap = kMindmapVGap,
}) {
  final childrenOf = <String, List<MindmapNodeItem>>{};
  final byId = {for (final n in nodes) n.id: n};
  final roots = <MindmapNodeItem>[];
  for (final n in nodes) {
    final parent = n.parentId;
    if (parent == null || !byId.containsKey(parent)) {
      roots.add(n);
    } else {
      childrenOf.putIfAbsent(parent, () => []).add(n);
    }
  }

  final positions = <String, Offset>{};
  final visiting = <String>{};
  var cursorY = 0.0;

  double place(MindmapNodeItem n, int depth) {
    // 已布节点：复用位置（重复引用）
    if (positions.containsKey(n.id)) return positions[n.id]!.dy;
    // 环引用（下钻途中再次遇到）：中断递归按叶子占行
    if (visiting.contains(n.id)) {
      final y = cursorY;
      cursorY += nodeHeight + vGap;
      return y;
    }
    visiting.add(n.id);
    final kids = childrenOf[n.id] ?? const <MindmapNodeItem>[];
    double y;
    if (kids.isEmpty) {
      y = cursorY;
      cursorY += nodeHeight + vGap;
    } else {
      var sum = 0.0;
      for (final k in kids) {
        sum += place(k, depth + 1);
      }
      y = sum / kids.length;
    }
    visiting.remove(n.id);
    positions[n.id] = Offset(depth * (nodeWidth + hGap), y);
    return y;
  }

  for (final r in roots) {
    place(r, 0);
  }
  // 环引用兜底：无根可达的剩余节点按伪根布设
  for (final n in nodes) {
    if (!positions.containsKey(n.id)) place(n, 0);
  }

  final width = positions.isEmpty
      ? nodeWidth
      : positions.values.map((p) => p.dx).reduce(math.max) + nodeWidth;
  final height = math.max(cursorY - vGap, nodeHeight);
  return MindmapLayoutResult(
    positions: positions,
    canvasSize: Size(width, height),
  );
}

/// 图形化知识导图画布（task_15 D1）：贝塞尔连线 + 圆角节点，
/// InteractiveViewer 缩放平移；点击节点回调（子坐标系命中）。
class MindmapCanvas extends StatelessWidget {
  final List<MindmapNodeItem> nodes;
  final ValueChanged<String> onNodeSelected;

  const MindmapCanvas({
    Key? key,
    required this.nodes,
    required this.onNodeSelected,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final layout = layoutMindmapTree(nodes);

    return InteractiveViewer(
      boundaryMargin: const EdgeInsets.all(60.0),
      minScale: 0.4,
      maxScale: 2.2,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapUp: (details) {
          final p = details.localPosition;
          for (final node in nodes) {
            final pos = layout.positions[node.id];
            if (pos == null) continue;
            final rect = Rect.fromLTWH(
                pos.dx, pos.dy, kMindmapNodeWidth, kMindmapNodeHeight);
            if (rect.contains(p)) {
              onNodeSelected(node.label);
              return;
            }
          }
        },
        child: SizedBox(
          width: layout.canvasSize.width,
          height: layout.canvasSize.height,
          child: CustomPaint(
            painter: _MindmapPainter(
              nodes: nodes,
              positions: layout.positions,
              isDark: isDark,
            ),
          ),
        ),
      ),
    );
  }
}

class _MindmapPainter extends CustomPainter {
  final List<MindmapNodeItem> nodes;
  final Map<String, Offset> positions;
  final bool isDark;

  _MindmapPainter({
    required this.nodes,
    required this.positions,
    required this.isDark,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final borderColor =
        isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final surfaceColor =
        isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final textColor =
        isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final accent = isDark
        ? ReaderTheme.darkAccentFocus
        : ReaderTheme.lightAccentFocus;

    // 先画连线（贝塞尔）
    final edgePaint = Paint()
      ..color = borderColor.withOpacity(0.9)
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    final byId = {for (final n in nodes) n.id: n};
    for (final n in nodes) {
      final parentPos = n.parentId == null ? null : positions[n.parentId];
      final selfPos = positions[n.id];
      if (parentPos == null || selfPos == null) continue;
      final start = Offset(parentPos.dx + kMindmapNodeWidth,
          parentPos.dy + kMindmapNodeHeight / 2);
      final end = Offset(selfPos.dx, selfPos.dy + kMindmapNodeHeight / 2);
      final midX = (start.dx + end.dx) / 2;
      final path = Path()
        ..moveTo(start.dx, start.dy)
        ..cubicTo(midX, start.dy, midX, end.dy, end.dx, end.dy);
      canvas.drawPath(path, edgePaint);
    }

    // 再画节点
    for (final n in nodes) {
      final pos = positions[n.id];
      if (pos == null) continue;
      final rect = Rect.fromLTWH(
          pos.dx, pos.dy, kMindmapNodeWidth, kMindmapNodeHeight);
      final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(8.0));

      final isRoot = (byId[n.id]?.depth ?? 0) == 0;
      canvas.drawRRect(
        rrect,
        Paint()..color = surfaceColor,
      );
      canvas.drawRRect(
        rrect,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = isRoot ? 1.5 : 1.0
          ..color = isRoot ? accent : borderColor,
      );

      final tp = TextPainter(
        text: TextSpan(
          text: n.label,
          style: TextStyle(
            fontFamily: 'iA Writer Mono',
            fontSize: isRoot ? 11.5 : 11.0,
            fontWeight: isRoot ? FontWeight.w600 : FontWeight.w400,
            color: isRoot ? textColor : textColor.withOpacity(0.85),
          ),
        ),
        maxLines: 1,
        ellipsis: '…',
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: kMindmapNodeWidth - 12.0);
      tp.paint(
        canvas,
        Offset(rect.left + 6.0,
            rect.center.dy - tp.height / 2),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _MindmapPainter old) =>
      old.nodes != nodes || old.positions != positions || old.isDark != isDark;
}
