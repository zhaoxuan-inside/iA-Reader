import 'dart:convert';

/// 标注样式分类（task_13 D1）：
/// 背景类（高亮/半高亮）、线条类（下划线/波浪线/删除线）、字型类（加粗/斜体）、批注类
enum AnnotationStyle {
  highlight('highlight', '高亮'),
  halfHighlight('half_highlight', '半高亮'),
  underline('underline', '下划线'),
  wavy('wavy', '波浪线'),
  strike('strike', '删除线'),
  bold('bold', '加粗'),
  italic('italic', '斜体'),
  marginNote('margin_note', '批注'),
  unknown('unknown', '未知');

  final String key;
  final String label;
  const AnnotationStyle(this.key, this.label);

  static AnnotationStyle fromKey(String? key) {
    for (final s in AnnotationStyle.values) {
      if (s.key == key) return s;
    }
    return AnnotationStyle.unknown;
  }
}

/// 样式分类组（面板分组展示用，不含 marginNote/unknown）
final Map<String, List<AnnotationStyle>> annotationStyleGroups = {
  '背景': [AnnotationStyle.highlight, AnnotationStyle.halfHighlight],
  '线条': [AnnotationStyle.underline, AnnotationStyle.wavy, AnnotationStyle.strike],
  '字型': [AnnotationStyle.bold, AnnotationStyle.italic],
};

/// 固定调色板（task_13 D2）：琥珀为默认高亮主色（DESIGN.md highlight-mark）
class AnnotationColorSpec {
  final String hex;
  final String label;
  const AnnotationColorSpec(this.hex, this.label);
}

const List<AnnotationColorSpec> annotationColorPalette = [
  AnnotationColorSpec('#CA8A04', '琥珀'),
  AnnotationColorSpec('#007AFF', '蓝'),
  AnnotationColorSpec('#34C759', '绿'),
  AnnotationColorSpec('#FF375F', '红'),
  AnnotationColorSpec('#AF52DE', '紫'),
  AnnotationColorSpec('#8E8E93', '灰'),
];

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
    this.colorHex = '#CA8A04',
    this.noteText,
  });

  bool get hasRange =>
      startOffset != null && endOffset != null && endOffset! > startOffset!;

  bool get isNote => style == AnnotationStyle.marginNote;

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
      colorHex: (row['color'] as String?) ?? '#CA8A04',
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
