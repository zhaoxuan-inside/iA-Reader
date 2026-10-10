// frontend/lib/features/reader/reader_controller.dart
import 'package:flutter/foundation.dart';
import '../../core/bridge.dart';

class ReaderController extends ChangeNotifier {
  int currentBookId = 0;
  String currentTitle = "";
  bool isGraphVisible = false;
  bool isMindmapVisible = false;
  bool isDualModeCanvas = false;
  String selectedText = "";
  List<Map<String, dynamic>> annotations = [];
  Map<String, dynamic> activeCompanionCard = {};

  void loadBook(int bookId, String title) {
    currentBookId = bookId;
    currentTitle = title;
    final res = ReaderBridge.instance.invoke("doc.get", {"book_id": bookId});
    notifyListeners();
  }

  void onSelectText(String text, int pageIndex, int offset) {
    selectedText = text;
    notifyListeners();
  }

  void openMarginNote(int annotationId) {
    final note = annotations.firstWhere((a) => a['id'] == annotationId, orElse: () => {});
    if (note.isNotEmpty) {
      activeCompanionCard = note;
      notifyListeners();
    }
  }

  void invokeAiCompanion(String templateType, String prompt) {
    final res = ReaderBridge.instance.invoke("ai.companion_ask", {
      "book_id": currentBookId,
      "template_type": templateType,
      "selected_text": selectedText,
      "prompt": prompt,
    });
    activeCompanionCard = {
      "template_type": templateType,
      "prompt": prompt,
      "response": res['data']?['response'] ?? "伴读生成完成",
    };
    notifyListeners();
  }

  void toggleGraphView() {
    isGraphVisible = !isGraphVisible;
    if (isGraphVisible) isMindmapVisible = false;
    notifyListeners();
  }

  void toggleMindmapView() {
    isMindmapVisible = !isMindmapVisible;
    if (isMindmapVisible) isGraphVisible = false;
    notifyListeners();
  }

  String exportAnnotationsMarkdown() {
    final buffer = StringBuffer();
    buffer.writeln("# 《$currentTitle》 阅读批注导览\n");
    for (var a in annotations) {
      buffer.writeln("> ${a['selected_text'] ?? ''}\n");
      buffer.writeln("**边注**：${a['note_text'] ?? ''}\n");
    }
    return buffer.toString();
  }
}
