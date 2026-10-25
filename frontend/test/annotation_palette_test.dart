// 标注面板测试（验收定稿交互：样式/颜色两维独立选择 → 「应用」提交组合）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_item.dart';
import 'package:ai_reader_frontend/features/annotation/presentation/annotation_palette.dart';

void main() {
  testWidgets('分组渲染 + 样式与颜色独立选择 + 应用提交组合', (tester) async {
    // 面板为无状态组件:StatefulBuilder 夹具模拟宿主持有选择态并回灌重建
    var selectedStyle = AnnotationStyle.highlight;
    var selectedColor = '#CA8A04';
    AnnotationStyle? appliedStyle;
    String? appliedColor;
    var applyCount = 0;
    var noteRequested = false;
    late StateSetter setSheet;

    await tester.pumpWidget(StatefulBuilder(
      builder: (context, setState) {
        setSheet = setState;
        return MaterialApp(
          home: Scaffold(
            body: AnnotationPalette(
              selectedStyle: selectedStyle,
              selectedColorHex: selectedColor,
              onStyleSelected: (s) => setSheet(() => selectedStyle = s),
              onColorSelected: (hex) => setSheet(() => selectedColor = hex),
              onApply: (style, colorHex) {
                appliedStyle = style;
                appliedColor = colorHex;
                applyCount++;
              },
              onNoteRequested: () => noteRequested = true,
              onClose: () {},
            ),
          ),
        );
      },
    ));

    // 分组标签（iA 语言：文字分组，无 emoji）
    expect(find.text('背景'), findsOneWidget);
    expect(find.text('线条'), findsOneWidget);
    expect(find.text('字型'), findsOneWidget);
    expect(find.text('颜色'), findsOneWidget);

    // 七种样式按钮 + 应用/批注入口
    for (final label in ['高亮', '半高亮', '下划线', '波浪线', '删除线', '加粗', '斜体']) {
      expect(find.text(label), findsOneWidget, reason: label);
    }
    expect(find.byKey(const ValueKey('palette_apply')), findsOneWidget);
    expect(find.text('批注'), findsOneWidget);

    // 六色圆点
    for (final c in annotationColorPalette) {
      expect(find.byKey(ValueKey('palette_color_${c.hex}')), findsOneWidget, reason: c.hex);
    }

    // 维度一：点样式 = 仅选择，不应用
    await tester.tap(find.byKey(const ValueKey('palette_style_wavy')));
    await tester.pump();
    expect(applyCount, 0, reason: '点样式不得立即应用');

    // 维度二：点颜色 = 仅选择
    await tester.tap(find.byKey(const ValueKey('palette_color_#007AFF')));
    await tester.pump();
    expect(applyCount, 0, reason: '点颜色不得立即应用');

    // 组合提交：应用 = 波浪线 × 蓝
    await tester.tap(find.byKey(const ValueKey('palette_apply')));
    expect(applyCount, 1);
    expect(appliedStyle, AnnotationStyle.wavy);
    expect(appliedColor, '#007AFF');

    // 批注入口独立可用
    await tester.tap(find.text('批注'));
    expect(noteRequested, isTrue);
  });

  testWidgets('样式选择态可视：选中样式带强调色下边线', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: AnnotationPalette(
          selectedStyle: AnnotationStyle.halfHighlight,
          selectedColorHex: '#CA8A04',
          onStyleSelected: (_) {},
          onColorSelected: (_) {},
          onApply: (_, __) {},
          onNoteRequested: () {},
          onClose: () {},
        ),
      ),
    ));
    await tester.pump();

    BorderSide sideOf(Key k) {
      final decor = (tester.widget(find.byKey(k)) as Container).decoration as BoxDecoration;
      return (decor.border as Border).bottom;
    }

    expect(sideOf(const ValueKey('palette_style_half_highlight')).color.a, 1.0,
        reason: '选中态下边线可见');
    expect(sideOf(const ValueKey('palette_style_highlight')).color.a, 0.0,
        reason: '未选中态下边线透明');
  });
}
