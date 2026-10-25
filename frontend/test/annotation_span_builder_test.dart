// 标注区间 TextSpan 构建测试（task_12 D5：高亮选区级）
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_span_builder.dart';

// 默认色与 builder 的 withValues(alpha: 0.35) 精确一致
// （旧 withOpacity 为字节舍入 0x59≈0.349，迁移精确 API 后以构造式对齐）
AnnotationRange _hl(int start, int end, [Color color = const Color(0xFFCA8A04)]) =>
    AnnotationRange(start: start, end: end, style: AnnotationStyle.highlight, color: color.withValues(alpha: 0.35));

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
      expect((children[2] as TextSpan).style!.backgroundColor, Colors.red.withValues(alpha: 0.35));
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

  group('全样式渲染映射（task_13 D1）', () {
    test('下划线', () {
      final span = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.underline, color: Colors.blue)],
          baseStyle: base);
      final s = (span.children![0] as TextSpan).style!;
      expect(s.decoration, TextDecoration.underline);
      expect(s.decorationStyle, TextDecorationStyle.solid);
      expect(s.backgroundColor, isNull);
    });

    test('波浪线', () {
      final span = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.wavy, color: Colors.green)],
          baseStyle: base);
      final s = (span.children![0] as TextSpan).style!;
      expect(s.decoration, TextDecoration.underline);
      expect(s.decorationStyle, TextDecorationStyle.wavy);
      expect(s.decorationColor, Colors.green);
    });

    test('删除线', () {
      final span = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.strike, color: Colors.red)],
          baseStyle: base);
      expect((span.children![0] as TextSpan).style!.decoration, TextDecoration.lineThrough);
    });

    test('加粗 / 斜体', () {
      final bold = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.bold, color: Colors.black)],
          baseStyle: base);
      expect((bold.children![0] as TextSpan).style!.fontWeight, FontWeight.w700);

      final italic = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.italic, color: Colors.black)],
          baseStyle: base);
      expect((italic.children![0] as TextSpan).style!.fontStyle, FontStyle.italic);
    });

    test('半高亮：背景带 shader 只画行框下半，与高亮同观感', () {
      final span = AnnotationSpanBuilder.build(
          text: text,
          ranges: [const AnnotationRange(start: 0, end: 2, style: AnnotationStyle.halfHighlight, color: Colors.amber)],
          baseStyle: const TextStyle(fontSize: 20.0, height: 1.8));
      final s = (span.children![0] as TextSpan).style!;
      // 背景带方案：无装饰线，背景 Paint 携带「上透明/下实」渐变 shader
      expect(s.decoration, isNull);
      expect(s.backgroundColor, isNull);
      expect(s.background, isNotNull);
      expect(s.background!.shader, isNotNull);
    });
  });
}
