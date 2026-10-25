import 'package:flutter/material.dart';

import 'annotation_item.dart';

export 'annotation_item.dart' show AnnotationStyle;

/// 区间标注（段落内 [start, end) 偏移）
class AnnotationRange {
  final int start;
  final int end;
  final AnnotationStyle style;
  final Color color;

  const AnnotationRange({
    required this.start,
    required this.end,
    this.style = AnnotationStyle.highlight,
    required this.color,
  });
}

/// 按 offset 区间把段落纯文本切分为带样式的 TextSpan 树（纯函数 seam）。
/// task_12/13：高亮=背景色内联；半高亮=粗底线模拟下半高亮；线条类=TextDecoration；
/// 字型类=fontWeight/fontStyle。
class AnnotationSpanBuilder {
  static TextSpan build({
    required String text,
    required List<AnnotationRange> ranges,
    TextStyle? baseStyle,
  }) {
    if (ranges.isEmpty) {
      return TextSpan(text: text, style: baseStyle);
    }

    final sorted = ranges.toList()
      ..sort((a, b) => a.start.compareTo(b.start));

    final spans = <TextSpan>[];
    var cursor = 0;
    for (final r in sorted) {
      final start = r.start.clamp(0, text.length);
      final end = r.end.clamp(0, text.length);
      if (end <= start) continue;
      if (start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, start), style: baseStyle));
      } else if (end <= cursor) {
        // 完全被前一区间覆盖
        continue;
      }
      final segStart = start > cursor ? start : cursor;
      // 标注样式覆盖基础样式（baseStyle 可能 inherit=false，反向 merge 会整段丢弃标注样式）
      final merged = baseStyle?.merge(_styleFor(r, baseStyle)) ?? _styleFor(r, baseStyle);
      spans.add(TextSpan(
        text: text.substring(segStart, end),
        style: merged,
      ));
      cursor = end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor), style: baseStyle));
    }

    return TextSpan(children: spans, style: baseStyle);
  }

  /// 半高亮背景带（验收定稿）：与高亮同色同透明度（alpha 0.35）的背景带，
  /// 只画行框的下半部分——垂直渐变 shader 于行高中线硬切（transparent→band），
  /// tileMode.repeated 周期=行高(fontSize×height)，跨行标注每行各在自己中线切半。
  /// [fontSize]/[heightMul] 必须与渲染 TextStyle 的实际值一致（palette 预览同用此函数）。
  static TextStyle halfHighlightBand(Color color, double fontSize, double heightMul) {
    final lineHeight = fontSize * heightMul;
    final bandColor = color.withValues(alpha: 0.35);
    const transparent = Color(0x00000000);
    return TextStyle(
      background: Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [transparent, transparent, bandColor, bandColor],
          stops: const [0.0, 0.499, 0.501, 1.0],
          tileMode: TileMode.repeated,
        ).createShader(Rect.fromLTWH(0, 0, 1000, lineHeight)),
    );
  }

  static TextStyle _styleFor(AnnotationRange r, TextStyle? baseStyle) {
    switch (r.style) {
      case AnnotationStyle.highlight:
        return TextStyle(backgroundColor: r.color.withValues(alpha: 0.35));
      case AnnotationStyle.halfHighlight:
        // TextSpan 背景无法直接裁半：渐变 shader 实现「高亮带的下半部分」，
        // 视觉验收标准 = 与高亮同观感、切分于行框中线、底边与高亮底对齐
        //（golden 像素验证见 annotation_styles_visual_test.dart）
        final fontSize = baseStyle?.fontSize ?? 16.0;
        final heightMul = baseStyle?.height ?? 1.4;
        return halfHighlightBand(r.color, fontSize, heightMul);
      case AnnotationStyle.underline:
        return TextStyle(
          decoration: TextDecoration.underline,
          decorationColor: r.color,
          decorationStyle: TextDecorationStyle.solid,
          decorationThickness: 1.5,
        );
      case AnnotationStyle.wavy:
        return TextStyle(
          decoration: TextDecoration.underline,
          decorationColor: r.color,
          decorationStyle: TextDecorationStyle.wavy,
        );
      case AnnotationStyle.strike:
        return TextStyle(
          decoration: TextDecoration.lineThrough,
          decorationColor: r.color,
        );
      case AnnotationStyle.bold:
        return const TextStyle(fontWeight: FontWeight.w700);
      case AnnotationStyle.italic:
        return const TextStyle(fontStyle: FontStyle.italic);
      case AnnotationStyle.marginNote:
      case AnnotationStyle.unknown:
        return const TextStyle();
    }
  }
}

/// '#RRGGBB' / '#AARRGGBB' → Color（容错回退琥珀高亮色）
Color annotationColorFromHex(String hex) {
  var h = hex.replaceFirst('#', '');
  if (h.length == 6) h = 'FF$h';
  final v = int.tryParse(h, radix: 16);
  return v != null ? Color(v) : const Color(0xFFCA8A04);
}
