// test/annotation_styles_visual_test.dart
// 标注五样式视觉基线 golden：高亮/半高亮(双色)×下划线/波浪线/删除线
// 半高亮为粗 lineThrough 带（覆盖字形下半），此 golden 钉住其视觉几何。

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_reader_frontend/features/annotation/domain/annotation_span_builder.dart';

void main() {
  testWidgets('标注五样式渲染视觉基线', (tester) async {
    tester.view.physicalSize = const Size(1400, 460);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    const base = TextStyle(fontFamily: 'iA Writer Duo', fontSize: 26.0, height: 2.2, color: Color(0xFF111827));

    const amber = Color(0xFFCA8A04);
    const blue = Color(0xFF007AFF);
    const red = Color(0xFFFF375F);

    Widget line(String label, AnnotationStyle style, Color color) {
      final span = AnnotationSpanBuilder.build(
        text: '预写式日志保证事务原子性',
        ranges: [AnnotationRange(start: 2, end: 9, style: style, color: color)],
        baseStyle: base,
      );
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 24.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            SizedBox(
              width: 120.0,
              child: Text(label, style: base.copyWith(fontSize: 14.0, color: const Color(0xFF6B7280))),
            ),
            Expanded(child: SelectableText.rich(TextSpan(children: span.children))),
          ],
        ),
      );
    }

    await tester.pumpWidget(MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        backgroundColor: const Color(0xFFFAFAFA),
        body: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            line('高亮·琥珀', AnnotationStyle.highlight, amber),
            line('高亮·蓝', AnnotationStyle.highlight, blue),
            line('半高亮·琥珀', AnnotationStyle.halfHighlight, amber),
            line('半高亮·红', AnnotationStyle.halfHighlight, red),
            line('下划线', AnnotationStyle.underline, blue),
            line('波浪线', AnnotationStyle.wavy, const Color(0xFFAF52DE)),
            line('删除线', AnnotationStyle.strike, red),
          ],
        ),
      ),
    ));
    await tester.pumpAndSettle();

    await expectLater(find.byType(Scaffold), matchesGoldenFile('goldens/annotation_styles_visual.png'));
  });
}
