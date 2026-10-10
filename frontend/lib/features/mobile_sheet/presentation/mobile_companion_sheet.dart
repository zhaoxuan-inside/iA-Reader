import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';
import '../../selection_pill/presentation/floating_action_pill.dart';

/// 移动端半屏触控伴读抽屉 (MobileCompanionSheet)
/// 严格对标 DESIGN.md 与产品原型：单手拖拽柄、向上滑动展开全屏、向下轻扫立即收起
class MobileCompanionSheet extends StatelessWidget {
  final CognitiveTemplateType currentTemplate;
  final String analysisContent;
  final VoidCallback onDismiss;
  final VoidCallback onSaveAnnotation;

  const MobileCompanionSheet({
    Key? key,
    required this.currentTemplate,
    required this.analysisContent,
    required this.onDismiss,
    required this.onSaveAnnotation,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final textPrimary = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    return DraggableScrollableSheet(
      initialChildSize: 0.45, // 默认半屏高度
      minChildSize: 0.25,     // 向下滑动触发收起阈值
      maxChildSize: 0.90,     // 向上滑动最大近全屏
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: surfaceColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20.0)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(isDark ? 0.5 : 0.12),
                blurRadius: 16.0,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: Column(
            children: [
              // 拖拽柄 (Drag Handle)
              Container(
                margin: const EdgeInsets.only(top: 10.0, bottom: 6.0),
                width: 36.0,
                height: 4.0,
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF3F3F46) : const Color(0xFFD1D5DB),
                  borderRadius: BorderRadius.circular(2.0),
                ),
              ),

              // 标题栏
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      currentTemplate.label,
                      style: TextStyle(
                        fontSize: 15.0,
                        fontWeight: FontWeight.w600,
                        color: accentColor,
                      ),
                    ),
                    Row(
                      children: [
                        TextButton(
                          onPressed: onSaveAnnotation,
                          child: const Text('存为边注', style: TextStyle(fontSize: 13.0)),
                        ),
                        IconButton(
                          icon: Icon(Icons.close, size: 20.0, color: textSecondary),
                          onPressed: onDismiss,
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const Divider(height: 1.0),

              // 正文滚动视图
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(16.0),
                  children: [
                    Text(
                      analysisContent,
                      style: TextStyle(
                        fontSize: 15.0,
                        height: 1.65,
                        color: textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
