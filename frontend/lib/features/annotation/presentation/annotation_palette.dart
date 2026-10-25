import 'package:flutter/material.dart';

import '../../../core/theme/reader_theme.dart';
import '../domain/annotation_item.dart';
import '../domain/annotation_span_builder.dart';

/// 标注面板（验收定稿交互）：样式与颜色是两个独立维度——
/// 分别点选样式按钮与颜色圆点（均为选择态，不立即应用），
/// 组合确认后点「应用」提交（onApply 携带 样式×颜色 组合）。
/// iA 语言：文字按钮、按钮文案以自身样式预览渲染，零 emoji。
class AnnotationPalette extends StatelessWidget {
  final AnnotationStyle selectedStyle;
  final String selectedColorHex;
  final ValueChanged<AnnotationStyle> onStyleSelected;
  final ValueChanged<String> onColorSelected;
  final void Function(AnnotationStyle style, String colorHex) onApply;
  final VoidCallback onNoteRequested;
  final VoidCallback onClose;

  const AnnotationPalette({
    super.key,
    required this.selectedStyle,
    required this.selectedColorHex,
    required this.onStyleSelected,
    required this.onColorSelected,
    required this.onApply,
    required this.onNoteRequested,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    TextStyle previewStyle(AnnotationStyle style) {
      final color = annotationColorFromHex(selectedColorHex);
      final base = TextStyle(
        fontFamily: 'iA Writer Mono',
        fontSize: 12.0,
        height: 1.5,
        color: textColor,
      );
      if (style == AnnotationStyle.halfHighlight) {
        return base.merge(AnnotationSpanBuilder.halfHighlightBand(color, 12.0, 1.5));
      }
      return base.merge(TextStyle(
        backgroundColor:
            style == AnnotationStyle.highlight ? color.withValues(alpha: 0.35) : null,
        decoration: style == AnnotationStyle.underline || style == AnnotationStyle.wavy
            ? TextDecoration.underline
            : style == AnnotationStyle.strike
                ? TextDecoration.lineThrough
                : null,
        decorationColor: color,
        decorationStyle: style == AnnotationStyle.wavy
            ? TextDecorationStyle.wavy
            : TextDecorationStyle.solid,
        decorationThickness: 1.5,
        fontWeight: style == AnnotationStyle.bold ? FontWeight.w700 : null,
        fontStyle: style == AnnotationStyle.italic ? FontStyle.italic : null,
      ));
    }

    return Material(
      color: Colors.transparent,
      child: Container(
        width: 372.0,
        padding: const EdgeInsets.fromLTRB(14.0, 10.0, 14.0, 12.0),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(12.0),
          border: Border.all(color: borderColor, width: 1.0),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('标注', style: TextStyle(fontFamily: 'iA Writer Mono', fontSize: 12.5, fontWeight: FontWeight.w600, color: textColor, letterSpacing: 0.5)),
                GestureDetector(
                  onTap: onClose,
                  child: Text('关闭', style: TextStyle(fontSize: 11.5, color: textSecondary)),
                ),
              ],
            ),
            const SizedBox(height: 8.0),
            // 分组样式行（选择态：点选即切换当前样式，不立即应用）
            for (final group in annotationStyleGroups.entries) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 32.0,
                    child: Text(group.key,
                        style: TextStyle(fontSize: 11.0, color: textSecondary, letterSpacing: 0.4)),
                  ),
                  Expanded(
                    child: Wrap(
                      spacing: 6.0,
                      runSpacing: 4.0,
                      children: group.value
                          .map((s) {
                            final selected = s == selectedStyle;
                            return GestureDetector(
                              behavior: HitTestBehavior.opaque,
                              onTap: () => onStyleSelected(s),
                              child: Container(
                                key: ValueKey('palette_style_${s.key}'),
                                padding: const EdgeInsets.symmetric(horizontal: 6.0, vertical: 3.0),
                                decoration: BoxDecoration(
                                  // 选中态：强调色下边线（iA 极简指示）
                                  border: Border(
                                    bottom: BorderSide(
                                      color: selected ? accentColor : Colors.transparent,
                                      width: 2.0,
                                    ),
                                  ),
                                ),
                                child: Text(
                                  s.label,
                                  style: previewStyle(s).copyWith(
                                    fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                                  ),
                                ),
                              ),
                            );
                          })
                          .toList(),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4.0),
            ],
            const Divider(height: 14.0),
            // 调色板行（选择态：点选即切换当前颜色，与样式自由组合）
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                SizedBox(
                  width: 32.0,
                  child: Text('颜色',
                      style: TextStyle(fontSize: 11.0, color: textSecondary, letterSpacing: 0.4)),
                ),
                Expanded(
                  child: Row(
                    children: annotationColorPalette
                        .map((c) => GestureDetector(
                              key: ValueKey('palette_color_${c.hex}'),
                              onTap: () => onColorSelected(c.hex),
                              child: Container(
                                width: 20.0,
                                height: 20.0,
                                margin: const EdgeInsets.only(right: 8.0),
                                decoration: BoxDecoration(
                                  color: annotationColorFromHex(c.hex),
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: c.hex == selectedColorHex ? textColor : Colors.transparent,
                                    width: 2.0,
                                  ),
                                ),
                              ),
                            ))
                        .toList(),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10.0),
            // 组合提交行：「应用」提交当前 样式×颜色 组合；「批注」转入边注编辑
            Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => onApply(selectedStyle, selectedColorHex),
                    child: Container(
                      key: const ValueKey('palette_apply'),
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 7.0),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8.0),
                        border: Border.all(color: accentColor, width: 1.0),
                      ),
                      child: Center(
                        child: Text(
                          '应用',
                          style: TextStyle(
                              fontFamily: 'iA Writer Mono',
                              fontSize: 12.0,
                              fontWeight: FontWeight.w600,
                              color: accentColor,
                              letterSpacing: 0.5),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8.0),
                Expanded(
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: onNoteRequested,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 7.0),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8.0),
                        border: Border.all(color: borderColor, width: 0.8),
                      ),
                      child: Center(
                        child: Text('批注',
                            style: TextStyle(
                                fontFamily: 'iA Writer Mono',
                                fontSize: 12.0,
                                fontWeight: FontWeight.w500,
                                color: textColor,
                                letterSpacing: 0.5)),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
