import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';

enum CognitiveTemplateType {
  general('⚡️ 通俗', 'general'),
  logic('🔗 逻辑', 'logic'),
  critical('🧐 批判', 'critical'),
  term('📖 术语', 'term'),
  highlight('🖍 高亮', 'highlight');

  final String label;
  final String templateKey;
  const CognitiveTemplateType(this.label, this.templateKey);
}

/// 划词快速伴读胶囊 (Floating Action Pill)
/// 严格对标 DESIGN.md：圆角 20px 药丸造型、微阴影、直通 4 大认知模板
class FloatingActionPill extends StatelessWidget {
  final Function(CognitiveTemplateType template) onTemplateSelected;
  final VoidCallback? onDismiss;

  const FloatingActionPill({
    Key? key,
    required this.onTemplateSelected,
    this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;

    return Material(
      color: Colors.transparent,
      elevation: 0,
      child: Container(
        height: 38.0,
        padding: const EdgeInsets.symmetric(horizontal: 6.0),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(20.0),
          border: Border.all(color: borderColor, width: 1.0),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.4 : 0.08),
              blurRadius: 12.0,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: CognitiveTemplateType.values.map((tpl) {
            return InkWell(
              borderRadius: BorderRadius.circular(16.0),
              onTap: () => onTemplateSelected(tpl),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 6.0),
                child: Text(
                  tpl.label,
                  style: TextStyle(
                    fontSize: 13.0,
                    fontWeight: FontWeight.w500,
                    color: textColor,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}
