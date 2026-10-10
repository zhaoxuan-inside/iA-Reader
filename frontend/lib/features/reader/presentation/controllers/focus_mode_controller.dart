import 'package:flutter/foundation.dart';
import '../../../../core/theme/reader_theme.dart';

/// 聚焦模式与段落失焦弱化状态控制器 (FocusModeController)
/// 严格遵守 DESIGN.md 规范：焦点段落 100% 对比度，上下文段落柔和弱化至 65% 透明度
class FocusModeController extends ChangeNotifier {
  bool _isFocusModeEnabled = false;
  String? _activeParagraphId;
  String? _selectedText;
  bool _isCompanionDrawerOpen = false;

  bool get isFocusModeEnabled => _isFocusModeEnabled;
  String? get activeParagraphId => _activeParagraphId;
  String? get selectedText => _selectedText;
  bool get isCompanionDrawerOpen => _isCompanionDrawerOpen;

  /// 计算指定段落的透明度 (Opacity)
  double getParagraphOpacity(String paragraphId) {
    if (!_isFocusModeEnabled) {
      return 1.0; // 默认全部段落 100% 对比度
    }
    if (_activeParagraphId == null || _activeParagraphId == paragraphId) {
      return 1.0; // 当前焦点段落保持 100% 清晰
    }
    return ReaderTheme.focusDimOpacity; // 非焦点段落柔和淡化至 65%
  }

  /// 选中文本并发起伴读焦点
  void focusParagraph(String paragraphId, {String? selectedText}) {
    _isFocusModeEnabled = true;
    _activeParagraphId = paragraphId;
    _selectedText = selectedText;
    notifyListeners();
  }

  /// 快捷键 Cmd/Ctrl + D 切换聚焦模式
  void toggleFocusMode({String? currentVisibleParagraphId}) {
    _isFocusModeEnabled = !_isFocusModeEnabled;
    if (_isFocusModeEnabled && _activeParagraphId == null) {
      _activeParagraphId = currentVisibleParagraphId;
    } else if (!_isFocusModeEnabled) {
      _activeParagraphId = null;
      _selectedText = null;
    }
    notifyListeners();
  }

  /// 按 Esc 键或双击空白处退出失焦状态，恢复全明
  void exitFocusMode() {
    if (_isFocusModeEnabled || _selectedText != null) {
      _isFocusModeEnabled = false;
      _activeParagraphId = null;
      _selectedText = null;
      notifyListeners();
    }
  }

  /// 打开/关闭右侧伴读抽屉
  void setCompanionDrawerOpen(bool isOpen) {
    _isCompanionDrawerOpen = isOpen;
    notifyListeners();
  }
}
