// 胶囊锚定纯函数测试（task_12 D1：胶囊跟随鼠标位置）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/selection_pill/domain/pill_anchor.dart';

void main() {
  const screen = Size(1280, 720);

  group('anchorPillAtPointer', () {
    test('胶囊水平居中于指针，垂直悬于指针上方', () {
      final pos = anchorPillAtPointer(const Offset(700, 400), screen);
      // 水平：指针位于胶囊中心
      expect(pos.dx + PillAnchorMetrics.pillWidth / 2, closeTo(700, 0.5));
      // 垂直：胶囊底边在指针上方留出间隙
      expect(pos.dy + PillAnchorMetrics.pillHeight, closeTo(400 - PillAnchorMetrics.pointerGap, 0.5));
    });

    test('指针靠近右缘时 clamp 进窗口', () {
      final pos = anchorPillAtPointer(const Offset(1270, 400), screen);
      expect(pos.dx + PillAnchorMetrics.pillWidth,
          lessThanOrEqualTo(screen.width - PillAnchorMetrics.margin));
      expect(pos.dx, greaterThanOrEqualTo(PillAnchorMetrics.margin));
    });

    test('指针靠近左缘时 clamp 进窗口', () {
      final pos = anchorPillAtPointer(const Offset(4, 400), screen);
      expect(pos.dx, PillAnchorMetrics.margin);
    });

    test('指针靠近底缘时胶囊翻转/夹紧到可见区域', () {
      final pos = anchorPillAtPointer(const Offset(700, 715), screen);
      expect(pos.dy + PillAnchorMetrics.pillHeight,
          lessThanOrEqualTo(screen.height - PillAnchorMetrics.margin));
    });

    test('指针在顶栏之下时胶囊不遮顶栏（下限 56）', () {
      final pos = anchorPillAtPointer(const Offset(700, 20), screen);
      expect(pos.dy, greaterThanOrEqualTo(56.0));
    });
  });
}
