/// AI 键盘作用域解析（task_14 D3）：划词选区 > 聚焦段落 > 首段 > 空
class AiTarget {
  final String? paragraphId;
  final String text;
  final bool isFromSelection;

  const AiTarget({
    this.paragraphId,
    required this.text,
    required this.isFromSelection,
  });
}

AiTarget resolveAiTarget({
  String? selectionText,
  String? selectionParagraphId,
  String? activeParagraphId,
  required Map<String, String> paragraphTexts,
}) {
  if (selectionText != null && selectionText.trim().isNotEmpty) {
    return AiTarget(
      paragraphId: selectionParagraphId ?? activeParagraphId,
      text: selectionText,
      isFromSelection: true,
    );
  }
  if (activeParagraphId != null && paragraphTexts.containsKey(activeParagraphId)) {
    return AiTarget(
      paragraphId: activeParagraphId,
      text: paragraphTexts[activeParagraphId]!,
      isFromSelection: false,
    );
  }
  if (paragraphTexts.isNotEmpty) {
    final firstId = paragraphTexts.keys.first;
    return AiTarget(
      paragraphId: firstId,
      text: paragraphTexts[firstId]!,
      isFromSelection: false,
    );
  }
  return const AiTarget(paragraphId: null, text: '', isFromSelection: false);
}
