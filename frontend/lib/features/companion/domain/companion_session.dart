import 'package:flutter/foundation.dart';

/// 伴读对话条目
class CompanionDialogueItem {
  final String role; // 'user' | 'ai'
  final String content;

  const CompanionDialogueItem({required this.role, required this.content});
}

/// 伴读会话状态（FEAT-005 REQ-006）：生命周期挂在阅读工作台而非抽屉浮层——
/// 关闭抽屉再重开，对话流、TTFT 与追问线程不丢失。
/// 此前对话 State 随 FrostedModal 移除即销毁，重开抽屉只剩最新一条回复。
class CompanionSession extends ChangeNotifier {
  final List<CompanionDialogueItem> dialogues = [];
  /// 首帧到达时延（毫秒）：null = 尚未收到任何 delta
  int? ttftMs;
  /// 流式追问线程 id：原位追问沿用同线程恢复上下文
  String? threadId;
  bool isResponding = false;

  void resetWithAnalysis(String analysis, {int? ttft}) {
    dialogues
      ..clear()
      ..add(CompanionDialogueItem(role: 'ai', content: analysis));
    ttftMs = ttft;
    isResponding = false;
    notifyListeners();
  }

  void addUserMessage(String content) {
    dialogues.add(CompanionDialogueItem(role: 'user', content: content));
    notifyListeners();
  }

  /// 追加（或就地更新流式渲染中的）AI 回复。
  /// streamingKey 非空时按键定位进行中的回复做增量更新，渲染粒度 = poll 增量。
  void upsertAiMessage(String content, {Object? streamingKey}) {
    if (streamingKey != null) {
      final idx = dialogues.lastIndexWhere(
          (d) => d.role == 'ai' && identical(d, streamingKey));
      if (idx >= 0) {
        dialogues[idx] = CompanionDialogueItem(role: 'ai', content: content);
        notifyListeners();
        return;
      }
    }
    dialogues.add(CompanionDialogueItem(role: 'ai', content: content));
    notifyListeners();
  }

  /// 流式渲染：以最后一个 AI 条目为进行中回复做整体替换
  void updateLastAiMessage(String content) {
    final idx = dialogues.lastIndexWhere((d) => d.role == 'ai');
    if (idx < 0) {
      dialogues.add(CompanionDialogueItem(role: 'ai', content: content));
    } else {
      dialogues[idx] = CompanionDialogueItem(role: 'ai', content: content);
    }
    notifyListeners();
  }

  void setResponding(bool v) {
    isResponding = v;
    notifyListeners();
  }

  void setTtft(int ms) {
    ttftMs = ms;
    notifyListeners();
  }

  void setThreadId(String id) {
    threadId = id;
  }
}
