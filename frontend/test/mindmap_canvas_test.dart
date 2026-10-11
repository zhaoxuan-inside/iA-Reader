// 知识导图与词云测试（task_15）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/toc_mindmap/presentation/mindmap_canvas.dart';
import 'package:ai_reader_frontend/features/toc_mindmap/presentation/toc_mindmap_drawer.dart';
import 'package:ai_reader_frontend/features/toc_mindmap/presentation/word_cloud.dart';

MindmapNodeItem _n(String id, String label, int depth, {String? parent}) =>
    MindmapNodeItem(id: id, label: label, depth: depth, parentId: parent);

void main() {
  group('layoutMindmapTree 布局纯函数', () {
    test('链式树：x 随深度步进，单叶链同行排布', () {
      final result = layoutMindmapTree([
        _n('a', '根', 0),
        _n('b', '子', 1, parent: 'a'),
        _n('c', '孙', 2, parent: 'b'),
      ]);
      final a = result.positions['a']!;
      final b = result.positions['b']!;
      final c = result.positions['c']!;
      expect(c.dx, greaterThan(b.dx));
      expect(b.dx, greaterThan(a.dx));
      expect(c.dy, b.dy, reason: '单叶链整体同行（tidy tree）');
      expect(result.canvasSize.width, greaterThan(c.dx));
    });

    test('父节点 y = 子节点 y 均值（tidy tree）', () {
      final result = layoutMindmapTree([
        _n('r', '根', 0),
        _n('l1', '叶1', 1, parent: 'r'),
        _n('l2', '叶2', 1, parent: 'r'),
      ]);
      final r = result.positions['r']!;
      final l1 = result.positions['l1']!;
      final l2 = result.positions['l2']!;
      expect(l1.dy, lessThan(l2.dy), reason: '叶子按序占行');
      expect(r.dy, closeTo((l1.dy + l2.dy) / 2, 0.5));
    });

    test('双根与孤儿节点安全布局', () {
      final result = layoutMindmapTree([
        _n('r1', '根1', 0),
        _n('r2', '根2', 0),
        _n('x', '孤儿', 1, parent: 'ghost'),
      ]);
      expect(result.positions.length, 3);
      expect(result.positions['r1']!.dy, lessThan(result.positions['r2']!.dy));
    });

    test('环引用不死循环', () {
      final result = layoutMindmapTree([
        _n('a', 'A', 0, parent: 'b'),
        _n('b', 'B', 1, parent: 'a'),
      ]);
      expect(result.positions, isNotEmpty);
    });
  });

  group('cloudFontSizeForScore', () {
    test('单调递增且有界', () {
      final low = cloudFontSizeForScore(0.2);
      final mid = cloudFontSizeForScore(0.6);
      final high = cloudFontSizeForScore(1.0);
      expect(low, lessThan(mid));
      expect(mid, lessThan(high));
      expect(cloudFontSizeForScore(-1.0), cloudFontSizeForScore(0.0), reason: '下界 clamp');
      expect(cloudFontSizeForScore(2.0), cloudFontSizeForScore(1.0), reason: '上界 clamp');
    });
  });

  group('画布与抽屉', () {
    final nodes = [
      _n('m1', '分布式高可靠存储', 0),
      _n('m2', '预写式日志 (WAL)', 1, parent: 'm1'),
      _n('m3', '顺序写入与原子性', 2, parent: 'm2'),
      _n('m4', '崩溃恢复', 2, parent: 'm2'),
    ];
    final keywords = [
      const KeywordTagItem(word: '一致性', score: 0.95, count: 8),
      const KeywordTagItem(word: '日志', score: 0.4, count: 3),
    ];

    testWidgets('导图画布渲染并可点选节点（回调整节点含 sectionId）', (tester) async {
      MindmapNodeItem? tapped;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 360,
            height: 500,
            child: MindmapCanvas(
              nodes: nodes,
              onNodeSelected: (node) => tapped = node,
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(CustomPaint), findsAtLeastNWidgets(1));

      // 命中根节点中心（InteractiveViewer 子坐标 = 画布坐标，根在左上）
      final layout = layoutMindmapTree(nodes);
      final rootCenter = layout.positions['m1']! + const Offset(66, 17);
      await tester.tapAt(rootCenter);
      expect(tapped?.label, '分布式高可靠存储');
      expect(tapped?.sectionId, isNull, reason: '根节点无章节关联');

      // 带章节关联的子节点：回调携带 sectionId（task_16 联动跳转）
      MindmapNodeItem? tappedChild;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 360,
            height: 500,
            child: MindmapCanvas(
              nodes: [
                _n('a', '根章节', 0),
                _n('b', '子章节概念', 1, parent: 'a'),
              ].map((n) => MindmapNodeItem(
                    id: n.id,
                    label: n.label,
                    depth: n.depth,
                    parentId: n.parentId,
                    sectionId: n.id == 'b' ? 7 : null,
                  )).toList(),
              onNodeSelected: (node) => tappedChild = node,
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();
      final layout2 = layoutMindmapTree([
        _n('a', '根章节', 0),
        _n('b', '子章节概念', 1, parent: 'a'),
      ]);
      final childCenter = layout2.positions['b']! + const Offset(66, 17);
      await tester.tapAt(childCenter);
      expect(tappedChild?.label, '子章节概念');
      expect(tappedChild?.sectionId, 7);
    });

    testWidgets('抽屉三 Tab：目录/知识导图/词云，词云字号随权重', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 360,
            height: 620,
            child: TocMindmapDrawer(
              sections: const [
                TocSectionItem(id: 1, title: '第一章 存储可靠性'),
              ],
              mindmapNodes: nodes,
              keywords: keywords,
              activeSectionId: 1,
              onSectionSelected: (_) {},
              onKeywordSelected: (_) {},
              onNodeSelected: (label, sectionId) {},
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.text('章节目录'), findsOneWidget);
      expect(find.text('知识导图'), findsOneWidget);
      expect(find.text('词云'), findsOneWidget);

      // 切到导图 Tab → 画布出现
      await tester.tap(find.text('知识导图'));
      await tester.pumpAndSettle();
      expect(find.byType(MindmapCanvas), findsOneWidget);

      // 切到词云 Tab → 高分词字号大于低分词
      await tester.tap(find.text('词云'));
      await tester.pumpAndSettle();
      final highStyle = tester.widget<Text>(find.text('一致性')).style!;
      final lowStyle = tester.widget<Text>(find.text('日志')).style!;
      expect(highStyle.fontSize!, greaterThan(lowStyle.fontSize!));
    });
  });
}
