import 'package:flutter/material.dart';

import '../../../../core/theme/reader_theme.dart';
import 'toc_mindmap_drawer.dart';

/// 词云字号映射（task_15 D2）：score∈[0,1] → 11..26，clamp 有界单调
double cloudFontSizeForScore(double score) {
  final s = score.clamp(0.0, 1.0).toDouble();
  return 11.0 + s * 15.0;
}

/// 权重词云（task_15 D2）：字号/颜色强度随 score，附 ×count 徽标；iA 单色系零彩虹。
class WordCloud extends StatelessWidget {
  final List<KeywordTagItem> keywords;
  final ValueChanged<String> onKeywordSelected;

  const WordCloud({
    Key? key,
    required this.keywords,
    required this.onKeywordSelected,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary =
        isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accent = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    final sorted = keywords.toList()
      ..sort((a, b) => b.score.compareTo(a.score));

    return Wrap(
      spacing: 10.0,
      runSpacing: 8.0,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: sorted.map((kw) {
        final fontSize = cloudFontSizeForScore(kw.score);
        final strong = kw.score >= 0.8;
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => onKeywordSelected(kw.word),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                kw.word,
                style: TextStyle(
                  fontSize: fontSize,
                  fontWeight: strong ? FontWeight.w700 : FontWeight.w400,
                  color: strong ? accent : textColor.withOpacity(0.55 + kw.score * 0.45),
                  height: 1.2,
                ),
              ),
              const SizedBox(width: 3.0),
              Text(
                '×${kw.count}',
                style: TextStyle(
                  fontSize: 9.5,
                  color: textSecondary,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
