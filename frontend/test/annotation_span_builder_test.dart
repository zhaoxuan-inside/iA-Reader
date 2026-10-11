// 标注区间 TextSpan 构建测试（task_12 D5：高亮选区级）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_span_builder.dart';

AnnotationRange _hl(int start, int end, [Color color = const Color(0x59CA8A04)]) =>
    AnnotationRange(start: start, end: end, style: AnnotationStyle.highlight, color: color);

void main() {
  const text = '0123456789ABCDEF';
  const base = TextStyle(fontSize: 16, color: Colors.black);

  group('AnnotationSpanBuilder.build', () {
    test('无标注时返回单一基础样式全文 Span', () {
      final span = AnnotationSpanBuilder.build(text: text, ranges: const [], baseStyle: base);
      expect(span.toPlainText(), text);
      expect(span.style, base);
      expect(span.children, isNull);
    });

    test('区间标注只着色所选子串', () {
      final span = AnnotationSpanBuilder.build(text: text, ranges: [_hl(4, 9)], baseStyle: base);
      expect(span.toPlainText(), text);
      final children = span.children!;
      expect(children.length, 3);
      expect(children[0].toPlainText(), '0123');
      expect(children[0].style!.backgroundColor, isNull);
      expect(children[1].toPlainText(), '45678');
      expect(children[1].style!.backgroundColor, _hl(0, 0).color);
      expect(children[2].toPlainText(), '9ABCDEF');
      expect(children[2].style!.backgroundColor, isNull);
    });

    test('多个不重叠区间按顺序切分', () {
      final span = AnnotationSpanBuilder.build(
          text: text, ranges: [_hl(0, 2), _hl(5, 6, Colors.red)], baseStyle: base);
      final children = span.children!;
      expect(children.map((c) => c.toPlainText()).toList(),
          ['01', '234', '5', '6789ABCDEF']);
      expect((children[2] as TextSpan).style!.backgroundColor, Colors.red);
    });

    test('区间越界被夹紧，空区间被忽略', () {
      final span = AnnotationSpanBuilder.build(
          text: text, ranges: [_hl(-3, 2), _hl(20, 30), _hl(8, 8)], baseStyle: base);
      final children = span.children!;
      expect(children.first.toPlainText(), '01');
      expect(children.last.toPlainText(), '23456789ABCDEF');
      expect(children.any((c) => c.toPlainText().isEmpty), isFalse);
    });

    test('区间乱序输入仍产出顺序切片', () {
      final span = AnnotationSpanBuilder.build(
          text: text, ranges: [_hl(10, 12), _hl(2, 4)], baseStyle: base);
      final children = span.children!;
      expect(children.map((c) => c.toPlainText()).toList(),
          ['01', '23', '456789', 'AB', 'CDEF']);
    });
  });
}
