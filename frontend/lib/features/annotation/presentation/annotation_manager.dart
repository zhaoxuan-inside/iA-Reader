import 'package:flutter/material.dart';

import '../../../core/theme/reader_theme.dart';
import '../domain/annotation_item.dart';
import '../domain/annotation_span_builder.dart';

/// 标注管理列表条目（item + 摘录；摘录由调用方按段落文本裁剪）
class AnnotationListEntry {
  final AnnotationItem item;
  final String excerpt;

  const AnnotationListEntry({required this.item, required this.excerpt});
}

/// 标注管理弹窗内容（task_13 D5 + task_16 D2）：全书标注清单——
/// 样式名 + 色点 + 摘录 + 批注文本 + 编辑/删除。
/// 由 main.dart 以 FrostedModal 承载；点击正文标注区间或段落批注计数行打开。
class AnnotationManagerModal extends StatelessWidget {
  final List<AnnotationListEntry> entries;
  final ValueChanged<String> onDelete;
  final void Function(String annotationId, String currentNote) onEdit;
  final VoidCallback onClose;

  const AnnotationManagerModal({
    super.key,
    required this.entries,
    required this.onDelete,
    required this.onEdit,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return buildContent(onDelete: onDelete, onEdit: onEdit, onClose: onClose);
  }

  Widget buildContent({
    required ValueChanged<String> onDelete,
    required void Function(String annotationId, String currentNote) onEdit,
    required VoidCallback onClose,
  }) {
    return Builder(builder: (context) {
      final isDark = Theme.of(context).brightness == Brightness.dark;
      final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
      final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
      final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;

      return Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('标注管理',
                    style: TextStyle(
                        fontFamily: 'iA Writer Mono',
                        fontSize: 13.0,
                        fontWeight: FontWeight.w600,
                        color: textColor,
                        letterSpacing: 0.5)),
                GestureDetector(
                  onTap: onClose,
                  child: Text('关闭', style: TextStyle(fontSize: 11.5, color: textSecondary)),
                ),
              ],
            ),
            const SizedBox(height: 10.0),
            if (entries.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 32.0),
                child: Center(
                  child: Text('暂无标注——划词后点「标注」开始',
                      style: TextStyle(fontSize: 12.5, color: textSecondary)),
                ),
              )
            else
              Expanded(
                child: ListView.builder(
                  itemCount: entries.length,
                  itemBuilder: (context, i) {
                    final e = entries[i];
                    final color = annotationColorFromHex(e.item.colorHex);
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8.0),
                      padding: const EdgeInsets.all(10.0),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8.0),
                        border: Border.all(color: borderColor, width: 0.8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 10.0,
                                height: 10.0,
                                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                              ),
                              const SizedBox(width: 6.0),
                              Text(e.item.style.label,
                                  style: TextStyle(
                                      fontFamily: 'iA Writer Mono',
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w500,
                                      color: color)),
                              const Spacer(),
                              if (e.item.noteText != null && e.item.noteText!.isNotEmpty)
                                Tooltip(
                                  message: '编辑标注 ${e.item.id}',
                                  child: GestureDetector(
                                    onTap: () => onEdit(e.item.id, e.item.noteText!),
                                    child: Icon(Icons.edit_outlined, size: 15.0, color: textSecondary),
                                  ),
                                ),
                              if (e.item.noteText != null && e.item.noteText!.isNotEmpty)
                                const SizedBox(width: 8.0),
                              Tooltip(
                                message: '删除标注 ${e.item.id}',
                                child: GestureDetector(
                                  onTap: () => onDelete(e.item.id),
                                  child: Icon(Icons.delete_outline, size: 15.0, color: textSecondary),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6.0),
                          Text(e.excerpt,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 12.5, color: textColor, height: 1.5)),
                          if (e.item.noteText != null && e.item.noteText!.isNotEmpty) ...[
                            const SizedBox(height: 4.0),
                            Text(e.item.noteText!,
                                style: TextStyle(
                                    fontSize: 12.0,
                                    fontStyle: FontStyle.italic,
                                    color: textSecondary,
                                    height: 1.5)),
                          ],
                        ],
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      );
    });
  }
}
