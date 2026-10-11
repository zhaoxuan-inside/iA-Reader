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
/// task_12 渲染高亮 = 文本背景色内联，取代旧的整段 Container 背景。
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
      final merged = baseStyle?.merge(_styleFor(r)) ?? _styleFor(r);
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

  static TextStyle _styleFor(AnnotationRange r) {
    switch (r.style) {
      case AnnotationStyle.highlight:
        return TextStyle(backgroundColor: r.color);
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
