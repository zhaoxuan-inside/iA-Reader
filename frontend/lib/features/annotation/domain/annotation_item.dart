import 'dart:convert';

/// 标注样式（task_12 先落 highlight；task_13 扩展全样式分类）
enum AnnotationStyle {
  highlight,
  marginNote,
  unknown;

  static AnnotationStyle fromKey(String? key) {
    switch (key) {
      case 'highlight':
        return AnnotationStyle.highlight;
      case 'margin_note':
        return AnnotationStyle.marginNote;
      default:
        return AnnotationStyle.unknown;
    }
  }

  String get key {
    switch (this) {
      case AnnotationStyle.highlight:
        return 'highlight';
      case AnnotationStyle.marginNote:
        return 'margin_note';
      case AnnotationStyle.unknown:
        return 'unknown';
    }
  }
}

/// 选区级标注：anchor 携带段落内 [startOffset, endOffset) 偏移；
/// 无偏移的边注（margin note）仅锚定段落。
class AnnotationItem {
  final String id;
  final int bookId;
  final int? sectionId;
  final String paragraphId;
  final int? startOffset;
  final int? endOffset;
  final AnnotationStyle style;
  final String colorHex;
  final String? noteText;

  const AnnotationItem({
    required this.id,
    required this.bookId,
    this.sectionId,
    required this.paragraphId,
    this.startOffset,
    this.endOffset,
    this.style = AnnotationStyle.highlight,
    this.colorHex = '#FFE066',
    this.noteText,
  });

  bool get hasRange =>
      startOffset != null && endOffset != null && endOffset! > startOffset!;

  /// 归一化 annotation.list 行：
  /// - 真实后端行：anchor_json 为 JSON 字符串；
  /// - mock 行：anchor 为 Map，另带 paragraph_id 顶层字段。
  static AnnotationItem fromListRow(Map<String, dynamic> row) {
    Map<String, dynamic>? anchor;
    final raw = row['anchor'] ?? row['anchor_json'];
    if (raw is Map<String, dynamic>) {
      anchor = raw;
    } else if (raw is String && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map<String, dynamic>) anchor = decoded;
      } catch (_) {
        // 损坏的 anchor_json 视为段落级标注
      }
    }

    final pId = (anchor?['paragraph_id'] ?? row['paragraph_id'])?.toString() ?? 'p1';
    final start = (anchor?['start'] as num?)?.toInt();
    final end = (anchor?['end'] as num?)?.toInt();
    final section = (anchor?['section_id'] ?? row['section_id']) as num?;

    return AnnotationItem(
      id: row['id']?.toString() ?? '',
      bookId: (row['book_id'] as num?)?.toInt() ?? 0,
      sectionId: section?.toInt(),
      paragraphId: pId,
      startOffset: start,
      endOffset: end,
      style: AnnotationStyle.fromKey(row['style'] as String?),
      colorHex: (row['color'] as String?) ?? '#FFE066',
      noteText: row['note_text'] as String?,
    );
  }

  /// annotation.save 的 anchor 载荷（后端落库 anchor_json，零 schema 迁移）
  Map<String, dynamic> anchorPayload() => {
        'paragraph_id': paragraphId,
        if (sectionId != null) 'section_id': sectionId,
        if (startOffset != null) 'start': startOffset,
        if (endOffset != null) 'end': endOffset,
      };
}
