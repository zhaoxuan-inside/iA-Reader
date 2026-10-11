// 标注面板测试（task_13 D3：分类样式 + 调色板 + 批注入口）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_item.dart';
import 'package:ai_reader_frontend/features/annotation/presentation/annotation_palette.dart';

void main() {
  testWidgets('面板渲染四类分组、七种样式按钮、六色调色板与批注入口', (tester) async {
    var appliedStyle = AnnotationStyle.highlight;
    var appliedColor = '#CA8A04';
    var selectedColor = '';
    var noteRequested = false;

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: AnnotationPalette(
          selectedColorHex: '#CA8A04',
          onColorSelected: (hex) => selectedColor = hex,
          onStyleSelected: (style, colorHex) {
            appliedStyle = style;
            appliedColor = colorHex;
          },
          onNoteRequested: () => noteRequested = true,
          onClose: () {},
        ),
      ),
    ));

    // 分组标签（iA 语言：文字分组，无 emoji）
    expect(find.text('背景'), findsOneWidget);
    expect(find.text('线条'), findsOneWidget);
    expect(find.text('字型'), findsOneWidget);
    expect(find.text('颜色'), findsOneWidget);

    // 七种样式按钮
    for (final label in ['高亮', '半高亮', '下划线', '波浪线', '删除线', '加粗', '斜体']) {
      expect(find.text(label), findsOneWidget, reason: label);
    }
    // 批注入口
    expect(find.text('批注'), findsOneWidget);

    // 六色圆点
    for (final c in annotationColorPalette) {
      expect(find.byKey(ValueKey('palette_color_${c.hex}')), findsOneWidget, reason: c.hex);
    }

    // 选样式 + 换色回调
    await tester.tap(find.byKey(const ValueKey('palette_color_#007AFF')));
    expect(selectedColor, '#007AFF');
    await tester.tap(find.text('波浪线'));
    expect(appliedStyle, AnnotationStyle.wavy);
    expect(appliedColor, '#CA8A04');

    await tester.tap(find.text('批注'));
    expect(noteRequested, isTrue);
  });
}
