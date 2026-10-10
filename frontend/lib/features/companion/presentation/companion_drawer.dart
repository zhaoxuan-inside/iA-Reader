import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';
import '../../selection_pill/presentation/floating_action_pill.dart';

/// 伴读对话条目数据结构
class CompanionDialogueItem {
  final String role; // 'user' 或 'ai'
  final String content;

  CompanionDialogueItem({required this.role, required this.content});
}

/// 认知伴读抽屉 (CompanionDrawer)
/// 严格对标 DESIGN.md：380px 定宽、无干扰边框、卡片内原位追问与持久化边注归档
class CompanionDrawer extends StatefulWidget {
  final String selectedText;
  final CognitiveTemplateType currentTemplate;
  final String initialAnalysis;
  final VoidCallback onClose;
  final Future<void> Function(String noteContent) onSaveAnnotation;
  final Future<String> Function(String followUpQuestion) onAskFollowUp;

  const CompanionDrawer({
    Key? key,
    required this.selectedText,
    required this.currentTemplate,
    required this.initialAnalysis,
    required this.onClose,
    required this.onSaveAnnotation,
    required this.onAskFollowUp,
  }) : super(key: key);

  @override
  State<CompanionDrawer> createState() => _CompanionDrawerState();
}

class _CompanionDrawerState extends State<CompanionDrawer> {
  final List<CompanionDialogueItem> _dialogues = [];
  final TextEditingController _inputController = TextEditingController();
  bool _isSaving = false;
  bool _isResponding = false;

  @override
  void initState() {
    super.initState();
    _dialogues.add(CompanionDialogueItem(
      role: 'ai',
      content: widget.initialAnalysis,
    ));
  }

  Future<void> _handleSendFollowUp() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isResponding) return;

    setState(() {
      _dialogues.add(CompanionDialogueItem(role: 'user', content: text));
      _isResponding = true;
      _inputController.clear();
    });

    try {
      final answer = await widget.onAskFollowUp(text);
      if (mounted) {
        setState(() {
          _dialogues.add(CompanionDialogueItem(role: 'ai', content: answer));
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isResponding = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textPrimary = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    return Container(
      width: 380.0,
      decoration: BoxDecoration(
        color: surfaceColor,
        border: Border(left: BorderSide(color: borderColor, width: 1.0)),
      ),
      child: Column(
        crossAxisAlignment: CrossCrossAlignment.stretch,
        children: [
          // 头部：模板标签 + 存边注 + 关闭
          Container(
            height: 52.0,
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: borderColor, width: 1.0)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(
                      widget.currentTemplate.label,
                      style: TextStyle(
                        fontSize: 14.0,
                        fontWeight: FontWeight.w600,
                        color: accentColor,
                      ),
                    ),
                    const SizedBox(width: 8.0),
                    Text(
                      '认知洞察',
                      style: TextStyle(fontSize: 12.0, color: textSecondary),
                    ),
                  ],
                ),
                Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.bookmark_add_outlined, size: 20.0, color: textSecondary),
                      tooltip: '保存为段落边注',
                      onPressed: _isSaving
                          ? null
                          : () async {
                              setState(() => _isSaving = true);
                              await widget.onSaveAnnotation(_dialogues.map((d) => d.content).join('\n\n'));
                              if (mounted) {
                                setState(() => _isSaving = false);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('已持久化存为段落边注')),
                                );
                              }
                            },
                    ),
                    IconButton(
                      icon: Icon(Icons.close, size: 20.0, color: textSecondary),
                      tooltip: '收起伴读抽屉',
                      onPressed: widget.onClose,
                    ),
                  ],
                ),
              ],
            ),
          ),

          // 对话流式卡片区
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(16.0),
              itemCount: _dialogues.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12.0),
              itemBuilder: (context, index) {
                final item = _dialogues[index];
                final isUser = item.role == 'user';
                return Container(
                  padding: const EdgeInsets.all(12.0),
                  decoration: BoxDecoration(
                    color: isUser
                        ? (isDark ? const Color(0xFF27272A) : const Color(0xFFF3F4F6))
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(8.0),
                    border: isUser ? null : Border.all(color: borderColor, width: 1.0),
                  ),
                  child: Text(
                    item.content,
                    style: TextStyle(
                      fontSize: 14.0,
                      height: 1.6,
                      color: textPrimary,
                    ),
                  ),
                );
              },
            ),
          ),

          // 底部原位追问输入框 (In-card Follow-up Input)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: borderColor, width: 1.0)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputController,
                    onSubmitted: (_) => _handleSendFollowUp(),
                    decoration: InputDecoration(
                      hintText: '追问本段细节 (Enter 发送)...',
                      hintStyle: TextStyle(fontSize: 13.0, color: textSecondary),
                      border: InputBorder.none,
                      isDense: true,
                    ),
                    style: TextStyle(fontSize: 13.0, color: textPrimary),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.arrow_upward_rounded, size: 18.0, color: accentColor),
                  onPressed: _isResponding ? null : _handleSendFollowUp,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
