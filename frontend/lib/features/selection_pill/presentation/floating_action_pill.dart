import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';

enum CognitiveTemplateType {
  general('通俗', 'general'),
  logic('逻辑', 'logic'),
  critical('批判', 'critical'),
  term('术语', 'term'),
  highlight('高亮', 'highlight');

  final String label;
  final String templateKey;
  const CognitiveTemplateType(this.label, this.templateKey);
}

/// 划词快速伴读胶囊 (Floating Action Pill)
/// 严格对标 DESIGN.md 与 iA 语言：圆角 20px 药丸、发丝线边框、零投影零 emoji，
/// 直通 4 大认知模板（ADR_006）
class FloatingActionPill extends StatelessWidget {
  final Function(CognitiveTemplateType template) onTemplateSelected;
  final VoidCallback? onAnnotationPalette;
  final VoidCallback? onDismiss;

  const FloatingActionPill({
    super.key,
    required this.onTemplateSelected,
    this.onAnnotationPalette,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

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
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ...CognitiveTemplateType.values.map((tpl) {
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onTemplateSelected(tpl),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 6.0),
                  child: Text(
                    tpl.label,
                    style: TextStyle(
                      fontFamily: 'iA Writer Mono',
                      fontSize: 12.0,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0.5,
                      color: textColor,
                    ),
                  ),
                ),
              );
            }),
            if (onAnnotationPalette != null)
              GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: onAnnotationPalette,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 6.0),
                  child: Text(
                    '标注',
                    style: TextStyle(
                      fontFamily: 'iA Writer Mono',
                      fontSize: 12.0,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                      color: accentColor,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
