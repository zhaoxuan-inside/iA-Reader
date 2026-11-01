import 'package:flutter/material.dart';

import '../../../core/theme/reader_theme.dart';
import '../../selection_pill/presentation/floating_action_pill.dart';
import '../domain/companion_session.dart';

/// 认知伴读抽屉 (CompanionDrawer)
/// 严格对标 DESIGN.md：380px 定宽、无干扰边框、卡片内原位追问与持久化边注归档。
///
/// 对话状态外置于 [CompanionSession]（生命周期跟随阅读工作台）：
/// 关闭抽屉重开不丢上下文；流式渲染以 poll 增量刷新进行中的 AI 条目。
class CompanionDrawer extends StatefulWidget {
  final CompanionSession session;
  final CognitiveTemplateType currentTemplate;
  final VoidCallback onClose;
  final Future<void> Function(String noteContent) onSaveAnnotation;

  /// 原位追问：onPartial 在每个流式增量到达时回调（FEAT-005 真流式），
  /// 返回值为最终完整回复
  final Future<String> Function(String question, void Function(String partial) onPartial) onAskFollowUp;

  /// 最近一次伴读响应是否为离线降级卡片（响应前缀【离线模式】）
  final bool offlineMode;

  /// 打开伴读 LLM 设置对话框
  final VoidCallback? onOpenSettings;

  const CompanionDrawer({
    super.key,
    required this.session,
    required this.currentTemplate,
    required this.onClose,
    required this.onSaveAnnotation,
    required this.onAskFollowUp,
    this.offlineMode = false,
    this.onOpenSettings,
  });

  @override
  State<CompanionDrawer> createState() => _CompanionDrawerState();
}

class _CompanionDrawerState extends State<CompanionDrawer> {
  final TextEditingController _inputController = TextEditingController();
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    // 首次打开且会话为空：以当前分析文本播种首条 AI 条目
    if (widget.session.dialogues.isEmpty) {
      widget.session.resetWithAnalysis('');
    }
  }

  Future<void> _handleSendFollowUp() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || widget.session.isResponding) return;

    widget.session
      ..addUserMessage(text)
      ..setResponding(true)
      ..updateLastAiMessage('思考中…');
    _inputController.clear();

    try {
      final answer = await widget.onAskFollowUp(
        text,
        (partial) => widget.session.updateLastAiMessage(partial),
      );
      if (mounted) {
        widget.session.updateLastAiMessage(answer);
      }
    } catch (_) {
      if (mounted) {
        widget.session.updateLastAiMessage('追问失败，请重试。');
      }
    } finally {
      if (mounted) {
        widget.session.setResponding(false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderColor =
        isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textPrimary =
        isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary =
        isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor =
        isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    return AnimatedBuilder(
      animation: widget.session,
      builder: (context, _) {
        final ttft = widget.session.ttftMs;
        // FEAT-005 REQ-002：头部展示 [模板 · TTFT xxxms]——首帧时延是流式体验的验收指标
        final headerMeta = ttft != null ? '${widget.currentTemplate.label} · TTFT ${ttft}ms' : widget.currentTemplate.label;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 头部：模板标签 + TTFT + 存边注 + 关闭
            Container(
              height: 52.0,
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: borderColor, width: 1.0)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Flexible(
                          child: Text(
                            headerMeta,
                            style: TextStyle(
                              fontSize: 14.0,
                              fontWeight: FontWeight.w600,
                              color: accentColor,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8.0),
                        Text(
                          '认知洞察',
                          style: TextStyle(fontSize: 12.0, color: textSecondary),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    children: [
                      IconButton(
                        icon: Icon(Icons.bookmark_add_outlined,
                            size: 20.0, color: textSecondary),
                        tooltip: '保存为段落边注',
                        onPressed: _isSaving
                            ? null
                            : () async {
                                setState(() => _isSaving = true);
                                await widget.onSaveAnnotation(widget.session.dialogues
                                    .map((d) => d.content)
                                    .join('\n\n'));
                                if (!mounted) return;
                                setState(() => _isSaving = false);
                                ScaffoldMessenger.of(this.context).showSnackBar(
                                  const SnackBar(content: Text('已持久化存为段落边注')),
                                );
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

            // 离线降级提示：直达 LLM 设置
            if (widget.offlineMode && widget.onOpenSettings != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16.0, 12.0, 16.0, 0.0),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
                  decoration: BoxDecoration(
                    color: (isDark
                        ? const Color(0xFF27272A)
                        : const Color(0xFFF3F4F6)),
                    borderRadius: BorderRadius.circular(8.0),
                    border: Border.all(color: borderColor, width: 1.0),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.bolt_outlined,
                          size: 15.0,
                          color: isDark ? Colors.white60 : Colors.black54),
                      const SizedBox(width: 6.0),
                      Expanded(
                        child: Text(
                          '当前为离线启发伴读（未配置 API Key）',
                          style: TextStyle(
                              fontSize: 11.5,
                              color: isDark ? Colors.white70 : Colors.black54),
                        ),
                      ),
                      GestureDetector(
                        onTap: widget.onOpenSettings,
                        child: Text(
                          '立即配置 →',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // 对话流式卡片区
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(16.0),
                itemCount: widget.session.dialogues.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12.0),
                itemBuilder: (context, index) {
                  final item = widget.session.dialogues[index];
                  final isUser = item.role == 'user';
                  final isStreaming = !isUser &&
                      widget.session.isResponding &&
                      index == widget.session.dialogues.length - 1;
                  return Container(
                    padding: const EdgeInsets.all(12.0),
                    decoration: BoxDecoration(
                      color: isUser
                          ? (isDark
                              ? const Color(0xFF27272A)
                              : const Color(0xFFF3F4F6))
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(8.0),
                      border: isUser
                          ? null
                          : Border.all(color: borderColor, width: 1.0),
                    ),
                    child: isStreaming && item.content == '思考中…'
                        ? Row(
                            children: [
                              SizedBox(
                                width: 12.0,
                                height: 12.0,
                                child: CircularProgressIndicator(
                                    strokeWidth: 1.6, color: accentColor),
                              ),
                              const SizedBox(width: 8.0),
                              Text('正在组织回复…',
                                  style: TextStyle(
                                      fontSize: 13.0, color: textSecondary)),
                            ],
                          )
                        : Text(
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
                    icon: Icon(Icons.arrow_upward_rounded,
                        size: 18.0, color: accentColor),
                    onPressed:
                        widget.session.isResponding ? null : _handleSendFollowUp,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
