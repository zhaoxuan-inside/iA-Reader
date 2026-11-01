import 'package:flutter/material.dart';

import '../../annotation/domain/annotation_span_builder.dart';

/// 行内 Markdown 解析（FEAT-002 REQ-002）：
/// **粗体** / *斜体* / `代码` / ~~删除线~~ / [链接](url) / ![图](url)
///
/// 设计约束：批注区间以「展示纯文本」的字符偏移锚定，因此解析产出
/// (plainText, segments)——plainText 剥离标记符，segments 携带各片段的
/// 语义样式与在 plainText 中的 [start, end) 区间。批注高亮与行内语义
/// 在同一份纯文本坐标系上叠加，互不漂移。
class InlineSegment {
  final int start;
  final int end;
  final bool bold;
  final bool italic;
  final bool code;
  final bool strike;
  final bool link;

  const InlineSegment({
    required this.start,
    required this.end,
    this.bold = false,
    this.italic = false,
    this.code = false,
    this.strike = false,
    this.link = false,
  });
}

class InlineMarkdown {
  final String plainText;
  final List<InlineSegment> segments;

  const InlineMarkdown(this.plainText, this.segments);

  /// 行内标记符扫描器：按优先级匹配左右界对；未闭合的标记按普通文本保留。
  static InlineMarkdown parse(String raw) {
    final plain = StringBuffer();
    final segments = <InlineSegment>[];
    final n = raw.length;

    /// 从 pos 尝试匹配一个标记对；成功返回消耗的字符数，失败返回 null
    int? tryMatch(int pos) {
      final rest = raw.substring(pos);

      // 链接 [text](url) / 图片 ![alt](url)：展示文本部分，url 剥离
      for (final open in const ['![', '[']) {
        if (!rest.startsWith(open)) continue;
        final from = pos + open.length;
        final closeBracket = raw.indexOf(']', from);
        if (closeBracket < 0) continue;
        final hasUrl = closeBracket + 1 < n && raw.startsWith('(', closeBracket + 1);
        final endIdx = hasUrl ? raw.indexOf(')', closeBracket + 2) : closeBracket;
        if (endIdx < 0) continue;
        final inner = raw.substring(from, closeBracket);
        if (inner.isEmpty) continue;
        final segStart = plain.length;
        plain.write(inner);
        segments.add(InlineSegment(start: segStart, end: plain.length, link: true));
        return (endIdx + 1) - pos;
      }

      // 语义对标记：粗体/删除线/代码/斜体（** 必须先于 * 匹配）
      for (final entry in const [
        ('**', true, false, false, false),
        ('~~', false, false, false, true),
        ('`', false, false, true, false),
        ('*', false, true, false, false),
        ('_', false, true, false, false),
      ]) {
        final open = entry.$1;
        if (!rest.startsWith(open)) continue;
        final from = pos + open.length;
        final close = raw.indexOf(open, from);
        if (close < 0) continue;
        final inner = raw.substring(from, close);
        if (inner.isEmpty) continue;
        final segStart = plain.length;
        plain.write(inner);
        segments.add(InlineSegment(
          start: segStart,
          end: plain.length,
          bold: entry.$2,
          italic: entry.$3,
          code: entry.$4,
          strike: entry.$5,
        ));
        return (close + open.length) - pos;
      }
      return null;
    }

    var i = 0;
    while (i < n) {
      final consumed = tryMatch(i);
      if (consumed == null) {
        plain.write(raw[i]);
        i += 1;
      } else {
        i += consumed;
      }
    }

    return InlineMarkdown(plain.toString(), segments);
  }

  /// 组装段落 TextSpan：行内语义样式 ⊕ 批注区间样式（同一纯文本坐标系）。
  /// 复用 AnnotationSpanBuilder 做区间切分——每段先按批注区间切段，
  /// 再叠加该段落的行内语义样式，保证两套样式在字符级正确合并。
  static TextSpan buildParagraphSpan({
    required InlineMarkdown markdown,
    required List<AnnotationRange> ranges,
    TextStyle? baseStyle,
    required bool isDark,
  }) {
    final text = markdown.plainText;
    if (markdown.segments.isEmpty) {
      return AnnotationSpanBuilder.build(text: text, ranges: ranges, baseStyle: baseStyle);
    }

    final children = <TextSpan>[];
    var cursor = 0;
    // 按 plain 偏移排序遍历语义段
    final segs = markdown.segments.toList()
      ..sort((a, b) => a.start.compareTo(b.start));
    for (final seg in segs) {
      final s = seg.start.clamp(0, text.length);
      final e = seg.end.clamp(0, text.length);
      if (e <= s) continue;
      if (s > cursor) {
        children.add(AnnotationSpanBuilder.build(
          text: text.substring(cursor, s),
          ranges: ranges,
          baseStyle: baseStyle,
        ));
      }
      final semantic = _semanticStyle(seg, baseStyle, isDark);
      children.add(AnnotationSpanBuilder.build(
        text: text.substring(s, e),
        ranges: ranges,
        baseStyle: baseStyle?.merge(semantic) ?? semantic,
      ));
      cursor = e;
    }
    if (cursor < text.length) {
      children.add(AnnotationSpanBuilder.build(
        text: text.substring(cursor),
        ranges: ranges,
        baseStyle: baseStyle,
      ));
    }
    return TextSpan(children: children, style: baseStyle);
  }

  static TextStyle _semanticStyle(InlineSegment seg, TextStyle? baseStyle, bool isDark) {
    var style = const TextStyle();
    if (seg.bold) style = style.merge(const TextStyle(fontWeight: FontWeight.w700));
    if (seg.italic) style = style.merge(const TextStyle(fontStyle: FontStyle.italic));
    if (seg.strike) {
      style = style.merge(const TextStyle(decoration: TextDecoration.lineThrough));
    }
    if (seg.code) {
      style = style.merge(TextStyle(
        fontFamily: 'iA Writer Mono',
        fontSize: (baseStyle?.fontSize ?? 16.0) * 0.88,
        backgroundColor: isDark
            ? const Color(0x1AFFFFFF)
            : const Color(0x14000000),
      ));
    }
    if (seg.link) {
      style = style.merge(TextStyle(
        color: isDark ? const Color(0xFF7CB8FF) : const Color(0xFF0066CC),
        decoration: TextDecoration.underline,
        decorationStyle: TextDecorationStyle.solid,
      ));
    }
    return style;
  }
}
