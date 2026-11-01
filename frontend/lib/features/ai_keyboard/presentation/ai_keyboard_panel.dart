import 'package:flutter/material.dart';

import '../../../core/theme/reader_theme.dart';
import '../../selection_pill/presentation/floating_action_pill.dart';

/// 独立 AI 键盘（task_14）：底部停靠浮层，键帽式模板按钮 + 伴读入口 + 作用域提示。
/// 与划词胶囊解耦：无选区也可用（自动回退聚焦段落）。
class AiKeyboardPanel extends StatelessWidget {
  final String targetHint;
  final void Function(CognitiveTemplateType template) onTemplateSelected;
  final VoidCallback onOpenCompanion;
  final VoidCallback onClose;

  const AiKeyboardPanel({
    super.key,
    required this.targetHint,
    required this.onTemplateSelected,
    required this.onOpenCompanion,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accent = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    Widget keycap(String label, VoidCallback onTap,
        {Color? color, FontWeight weight = FontWeight.w500}) {
      return GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 9.0),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8.0),
            border: Border.all(color: borderColor, width: 1.0),
            color: isDark ? ReaderTheme.darkBgCanvas : ReaderTheme.lightBgCanvas,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontFamily: 'iA Writer Mono',
              fontSize: 12.5,
              fontWeight: weight,
              letterSpacing: 0.5,
              color: color ?? textColor,
            ),
          ),
        ),
      );
    }

    return Material(
      color: Colors.transparent,
      child: Container(
        width: 560.0,
        padding: const EdgeInsets.fromLTRB(16.0, 12.0, 16.0, 14.0),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(14.0),
          border: Border.all(color: borderColor, width: 1.0),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('AI 键盘',
                    style: TextStyle(
                        fontFamily: 'iA Writer Mono',
                        fontSize: 12.5,
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
            // 理解模板键帽区：数字键 1-4 直触（FEAT-010 REQ-003）
            Wrap(
              spacing: 8.0,
              runSpacing: 8.0,
              children: [
                for (final entry in const [
                  (CognitiveTemplateType.general, '1'),
                  (CognitiveTemplateType.logic, '2'),
                  (CognitiveTemplateType.critical, '3'),
                  (CognitiveTemplateType.term, '4'),
                ])
                  keycap('${entry.$2} ${entry.$1.label}',
                      () => onTemplateSelected(entry.$1)),
              ],
            ),
            const SizedBox(height: 10.0),
            // 伴读追问区
            Row(
              children: [
                keycap('认知伴读', onOpenCompanion, color: accent, weight: FontWeight.w600),
                const SizedBox(width: 10.0),
                Expanded(
                  child: Text(
                    targetHint,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: textSecondary, letterSpacing: 0.2),
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
