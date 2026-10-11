import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'core/theme/reader_theme.dart';
import 'core/ffi/reader_engine_bridge.dart';
import 'core/widgets/frosted_modal.dart';
import 'core/widgets/window_controls.dart';
import 'core/window/window_channel.dart';
import 'features/reader/presentation/controllers/focus_mode_controller.dart';
import 'features/selection_pill/presentation/floating_action_pill.dart';
import 'features/selection_pill/domain/pill_anchor.dart';
import 'features/annotation/domain/annotation_item.dart';
import 'features/annotation/domain/annotation_span_builder.dart';
import 'features/companion/presentation/companion_drawer.dart';
import 'features/mobile_sheet/presentation/mobile_companion_sheet.dart';
import 'features/toc_mindmap/presentation/toc_mindmap_drawer.dart';
import 'features/library/presentation/library_screen.dart';
import 'features/settings/presentation/settings_dialog.dart';

void main() {
  runApp(const AIReaderApp());
}

/// AI Reader 顶层 App
class AIReaderApp extends StatefulWidget {
  const AIReaderApp({Key? key}) : super(key: key);

  @override
  State<AIReaderApp> createState() => _AIReaderAppState();
}

class _AIReaderAppState extends State<AIReaderApp> {
  ThemeMode _themeMode = ThemeMode.dark;
  late final ReaderEngineBridge _bridge;

  // 视图状态：文件库 (Library) 与沉浸阅读 (Reader) 彻底解耦
  bool _isLibraryMode = false;
  int _currentBookId = 1;

  @override
  void initState() {
    super.initState();
    _bridge = ReaderEngineBridge();
  }

  void _toggleTheme() {
    setState(() {
      _themeMode = _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  void _openBook(int bookId) {
    setState(() {
      _currentBookId = bookId;
      _isLibraryMode = false;
    });
  }

  void _backToLibrary() {
    setState(() {
      _isLibraryMode = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = _themeMode == ThemeMode.dark;

    return MaterialApp(
      title: 'AI Reader',
      debugShowCheckedModeBanner: false,
      theme: ReaderTheme.lightTheme,
      darkTheme: ReaderTheme.darkTheme,
      themeMode: _themeMode,
      home: _isLibraryMode
          ? LibraryScreen(
              bridge: _bridge,
              onOpenBook: _openBook,
              onToggleTheme: _toggleTheme,
              isDarkMode: isDark,
            )
          : ReaderWorkbenchScreen(
              bridge: _bridge,
              initialBookId: _currentBookId,
              onBackToLibrary: _backToLibrary,
              onToggleTheme: _toggleTheme,
              isDarkMode: isDark,
            ),
    );
  }
}

/// 沉浸专注阅读工作台 (ReaderWorkbenchScreen)
/// 对标 iA Writer 纯粹打字机/长文沉浸哲学：
/// 1. 内容是一等公民（Typography-first），无文件系统噪音；
/// 2. 顶栏自动隐退，无框线扰动；
/// 3. 左侧目录与导图为按需浮现抽屉；
/// 4. 黄金版心定宽 700px 居中排版，衬线字体温润呼吸；
/// 5. 选区 Focus Mode 柔和弱化背景。
class ReaderWorkbenchScreen extends StatefulWidget {
  final ReaderEngineBridge bridge;
  final int initialBookId;
  final VoidCallback onBackToLibrary;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const ReaderWorkbenchScreen({
    Key? key,
    required this.bridge,
    this.initialBookId = 1,
    required this.onBackToLibrary,
    required this.onToggleTheme,
    required this.isDarkMode,
  }) : super(key: key);

  @override
  State<ReaderWorkbenchScreen> createState() => _ReaderWorkbenchScreenState();
}

class _ReaderWorkbenchScreenState extends State<ReaderWorkbenchScreen> {
  late final FocusModeController _focusController;
  final ScrollController _scrollController = ScrollController();

  // 顶栏自动淡出隐退控制 (iA Writer Immersion)
  bool _isHeaderVisible = true;
  double _lastScrollOffset = 0.0;

  // 文档状态
  late int _currentBookId;
  String _currentBookTitle = '分布式系统高可靠存储与认知解析';
  int _activeSectionId = 1;
  List<TocSectionItem> _tocSections = [];
  List<MindmapNodeItem> _mindmapNodes = [];
  List<KeywordTagItem> _keywords = [];
  List<Map<String, dynamic>> _paragraphs = [];
  // 段落锚点：划词胶囊定位到选区所在段落/选区矩形旁
  final Map<String, GlobalKey> _paraKeys = {};
  // 选区级标注（task_12 D5）：含高亮区间与边注，经 annotation.* FFI 持久化
  final List<AnnotationItem> _annotations = [];
  // 默认高亮色：DESIGN.md highlight-mark 琥珀黄（渲染时叠加 35% 透明度）
  static const String _defaultHighlightHex = '#CA8A04';

  // 抽屉状态：默认全关闭，给用户最纯净的开屏阅读世界
  bool _isTocOpen = false;
  String _activeAnalysisText = '';
  CognitiveTemplateType _activeTemplate = CognitiveTemplateType.general;
  // 最近一次伴读响应是否为离线降级卡片（驱动抽屉内"立即配置"提示）
  bool _companionOffline = false;
  Offset? _selectionPosition;
  String? _selectedTextCache;
  String? _selectedParagraphIdCache;
  // 选区在段落文本内的偏移（高亮/标注按区间锚定的数据源）
  int? _selStartCache;
  int? _selEndCache;
  // 最近指针全局坐标：胶囊跟随鼠标位置锚定（task_12 D1）
  Offset? _lastPointerGlobal;

  @override
  void initState() {
    super.initState();
    _currentBookId = widget.initialBookId;
    _focusController = FocusModeController();

    _scrollController.addListener(_handleScroll);
    _loadDocumentData(_currentBookId);
  }

  @override
  void didUpdateWidget(covariant ReaderWorkbenchScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialBookId != widget.initialBookId) {
      _currentBookId = widget.initialBookId;
      _loadDocumentData(_currentBookId);
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _focusController.dispose();
    super.dispose();
  }

  void _handleScroll() {
    final offset = _scrollController.offset;
    if (offset > 50 && offset > _lastScrollOffset) {
      if (_isHeaderVisible) {
        setState(() => _isHeaderVisible = false);
      }
    } else if (offset < _lastScrollOffset || offset <= 20) {
      if (!_isHeaderVisible) {
        setState(() => _isHeaderVisible = true);
      }
    }
    _lastScrollOffset = offset;
  }

  Future<void> _loadDocumentData(int bookId) async {
    // 1. 加载文档章节与段落
    final docRes = await widget.bridge.invoke('doc.get', {'book_id': bookId});
    if (docRes.isSuccess) {
      final docData = docRes.data;
      final sectionsData = (docData['sections'] as List<dynamic>?) ?? [];

      final loadedSections = <TocSectionItem>[];
      final loadedParagraphs = <Map<String, dynamic>>[];

      for (final sec in sectionsData) {
        final secId = sec['id'] as int;
        final secTitle = sec['title'] as String;
        final paras = (sec['paragraphs'] as List<dynamic>?) ?? [];

        loadedSections.add(TocSectionItem(
          id: secId,
          title: secTitle,
          startParagraphId: paras.isNotEmpty ? paras.first['id'] as String : null,
        ));

        for (final p in paras) {
          loadedParagraphs.add({
            'id': p['id'] as String,
            'section_id': secId,
            'text': p['text'] as String,
          });
        }
      }

      setState(() {
        _currentBookId = bookId;
        _currentBookTitle = docData['title'] ?? _currentBookTitle;
        _tocSections = loadedSections;
        _paragraphs = loadedParagraphs;
      });
    }

    // 2. 加载思维导图
    final mmRes = await widget.bridge.invoke('mindmap.generate', {'book_id': bookId});
    if (mmRes.isSuccess) {
      final nodes = (mmRes.data['nodes'] as List<dynamic>?) ?? [];
      setState(() {
        _mindmapNodes = nodes.map((n) {
          return MindmapNodeItem(
            id: n['id'].toString(),
            label: n['label'] ?? '',
            depth: n['depth'] as int? ?? 0,
            parentId: n['parent_id']?.toString(),
          );
        }).toList();
      });
    }

    // 3. 加载核心关键词
    final kwRes = await widget.bridge.invoke('nlp.keyword_extract', {'book_id': bookId});
    if (kwRes.isSuccess) {
      final kws = (kwRes.data['keywords'] as List<dynamic>?) ?? [];
      setState(() {
        _keywords = kws.map((k) {
          return KeywordTagItem(
            word: k['word'] ?? '',
            score: (k['score'] as num?)?.toDouble() ?? 0.5,
            count: k['count'] as int? ?? 1,
          );
        }).toList();
      });
    }

    // 4. 加载已有标注（高亮区间 + 边注），回填选区级渲染
    final annRes = await widget.bridge.invoke('annotation.list', {'book_id': bookId});
    if (annRes.isSuccess) {
      final anns = (annRes.data['annotations'] as List<dynamic>?) ?? [];
      setState(() {
        _annotations
          ..clear()
          ..addAll(anns
              .whereType<Map<String, dynamic>>()
              .map(AnnotationItem.fromListRow)
              .where((a) => a.paragraphId.isNotEmpty));
      });
    }
  }

  void _triggerCompanion(String paragraphId, String text, CognitiveTemplateType template) async {
    setState(() {
      _selectionPosition = null;
      _activeTemplate = template;
      _activeAnalysisText = '正在调用底层认知计算引擎深度解析中...';
    });
    _focusController.focusParagraph(paragraphId, selectedText: text);
    _focusController.setCompanionDrawerOpen(true);

    final res = await widget.bridge.invoke('ai.companion_ask', {
      'book_id': _currentBookId,
      'template_type': template.templateKey,
      'selected_text': text,
    });

    if (mounted) {
      setState(() {
        final respText = (res.data['response'] ?? res.data['analysis'] ?? '解析完成') as String;
        _activeAnalysisText = respText;
        _companionOffline = respText.startsWith('【离线模式】');
      });
    }
  }

  /// 高亮所选子串（task_12 D5）：按选区偏移锚定并持久化，不再整段着色
  Future<void> _handleHighlight() async {
    final pId = _selectedParagraphIdCache;
    final start = _selStartCache;
    final end = _selEndCache;
    _clearSelection();
    if (pId == null || start == null || end == null || end <= start) return;

    final paragraph = _paragraphs.firstWhere(
      (p) => p['id'] == pId,
      orElse: () => {'section_id': _activeSectionId},
    );
    final sectionId = (paragraph['section_id'] as int?) ?? _activeSectionId;

    final res = await widget.bridge.invoke('annotation.save', {
      'book_id': _currentBookId,
      'section_id': sectionId,
      'paragraph_id': pId,
      'style': 'highlight',
      'color': _defaultHighlightHex,
      'anchor': {
        'paragraph_id': pId,
        'section_id': sectionId,
        'start': start,
        'end': end,
      },
    });

    if (!mounted) return;
    setState(() {
      _annotations.add(AnnotationItem(
        id: res.data['annotation_id']?.toString() ??
            'local_${DateTime.now().millisecondsSinceEpoch}',
        bookId: _currentBookId,
        sectionId: sectionId,
        paragraphId: pId,
        startOffset: start,
        endOffset: end,
        style: AnnotationStyle.highlight,
        colorHex: _defaultHighlightHex,
      ));
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('已高亮所选内容'), duration: Duration(milliseconds: 1200)),
    );
  }

  void _clearSelection() {
    _selectionPosition = null;
    _selectedTextCache = null;
    _selectedParagraphIdCache = null;
    _selStartCache = null;
    _selEndCache = null;
  }

  void _focusNextParagraph() {
    if (_paragraphs.isEmpty) return;
    final currentId = _focusController.activeParagraphId;
    int idx = _paragraphs.indexWhere((p) => p['id'] == currentId);
    if (idx == -1 || idx >= _paragraphs.length - 1) {
      _focusController.focusParagraph(_paragraphs.first['id']!);
    } else {
      _focusController.focusParagraph(_paragraphs[idx + 1]['id']!);
    }
  }

  void _focusPrevParagraph() {
    if (_paragraphs.isEmpty) return;
    final currentId = _focusController.activeParagraphId;
    int idx = _paragraphs.indexWhere((p) => p['id'] == currentId);
    if (idx <= 0) {
      _focusController.focusParagraph(_paragraphs.last['id']!);
    } else {
      _focusController.focusParagraph(_paragraphs[idx - 1]['id']!);
    }
  }

  /// 划词胶囊定位：优先锚定选区末尾矩形（RenderParagraph 实测选区框），
  /// 回退到选区段落右上角；并夹紧到窗口可视范围内。
  Offset _computePillPosition(String pId, TextSelection selection) {
    const pillWidth = 240.0;
    const pillHeight = 38.0;
    const margin = 16.0;
    final screen = MediaQuery.of(context).size;
    Offset anchor = const Offset(260.0, 180.0);

    final ro = _paraKeys[pId]?.currentContext?.findRenderObject();
    if (ro is RenderBox && ro.hasSize) {
      final paraOrigin = ro.localToGlobal(Offset.zero);
      anchor = Offset(
        paraOrigin.dx + ro.size.width - pillWidth,
        paraOrigin.dy - pillHeight - 8.0,
      );
      final paragraph = _findRenderParagraph(ro);
      if (paragraph != null) {
        try {
          final boxes = paragraph.getBoxesForSelection(selection);
          if (boxes.isNotEmpty) {
            final globalEnd = paragraph.localToGlobal(boxes.last.toRect().bottomRight);
            anchor = Offset(globalEnd.dx - pillWidth * 0.6, globalEnd.dy + 10.0);
          }
        } catch (_) {
          // 选区盒计算失败时沿用段落右上角锚点
        }
      }
    }

    final dx = anchor.dx.clamp(margin, (screen.width - pillWidth - margin).clamp(margin, double.infinity));
    final dy = anchor.dy.clamp(56.0, screen.height - pillHeight - margin);
    return Offset(dx, dy);
  }

  RenderParagraph? _findRenderParagraph(RenderObject root) {
    if (root is RenderParagraph) return root;
    RenderParagraph? found;
    root.visitChildren((child) {
      found ??= _findRenderParagraph(child);
    });
    return found;
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024.0;
    final isDark = widget.isDarkMode;

    final canvasBg = isDark ? ReaderTheme.darkBgCanvas : ReaderTheme.lightBgCanvas;
    final surfaceBg = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    return Shortcuts(
      shortcuts: <LogicalKeySet, Intent>{
        LogicalKeySet(LogicalKeyboardKey.meta, LogicalKeyboardKey.keyD):
            const _ToggleFocusIntent(),
        LogicalKeySet(LogicalKeyboardKey.control, LogicalKeyboardKey.keyD):
            const _ToggleFocusIntent(),
        LogicalKeySet(LogicalKeyboardKey.meta, LogicalKeyboardKey.backslash):
            const _ToggleTocIntent(),
        LogicalKeySet(LogicalKeyboardKey.control, LogicalKeyboardKey.backslash):
            const _ToggleTocIntent(),
        LogicalKeySet(LogicalKeyboardKey.escape): const _ExitFocusIntent(),
        LogicalKeySet(LogicalKeyboardKey.keyJ): const _NextParagraphIntent(),
        LogicalKeySet(LogicalKeyboardKey.keyK): const _PrevParagraphIntent(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _ToggleFocusIntent: CallbackAction<_ToggleFocusIntent>(
            onInvoke: (_) => _focusController.toggleFocusMode(
              currentVisibleParagraphId: _paragraphs.isNotEmpty ? _paragraphs.first['id'] : null,
            ),
          ),
          _ToggleTocIntent: CallbackAction<_ToggleTocIntent>(
            onInvoke: (_) {
              setState(() => _isTocOpen = !_isTocOpen);
              return null;
            },
          ),
          _ExitFocusIntent: CallbackAction<_ExitFocusIntent>(
            onInvoke: (_) {
              if (_isTocOpen) {
                setState(() => _isTocOpen = false);
              }
              _focusController.exitFocusMode();
              _focusController.setCompanionDrawerOpen(false);
              setState(_clearSelection);
              return null;
            },
          ),
          _NextParagraphIntent: CallbackAction<_NextParagraphIntent>(
            onInvoke: (_) {
              _focusNextParagraph();
              return null;
            },
          ),
          _PrevParagraphIntent: CallbackAction<_PrevParagraphIntent>(
            onInvoke: (_) {
              _focusPrevParagraph();
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: AnimatedBuilder(
            animation: _focusController,
            builder: (context, _) {
              return Scaffold(
                backgroundColor: canvasBg,
                body: MouseRegion(
                  onHover: (e) {
                    // 仅当指针明确向上移动接近顶缘时才唤出顶栏：
                    // 纯位置接近（dy<48）会与「下滚隐退」互相触发——阅读时指针停在顶栏附近，
                    // 每次滚轮下滚隐退后，指针微动又唤出，顶栏与正文反复跳变形成持续抖动。
                    if (!_isHeaderVisible &&
                        e.position.dy < 48 &&
                        e.delta.dy < -1.0) {
                      setState(() => _isHeaderVisible = true);
                    }
                  },
                  child: Stack(
                    children: [
                      Column(
                        children: [
                          // 1. 极简自动隐退顶栏 (DESIGN.md §4.1: 44px 高度，无边框喧宾夺主)
                          AnimatedContainer(
                            duration: ReaderTheme.chromeFadeDuration,
                            curve: Curves.easeInOut,
                            height: _isHeaderVisible ? 44.0 : 0.0,
                            child: AnimatedOpacity(
                              duration: ReaderTheme.chromeFadeDuration,
                              opacity: _isHeaderVisible ? 1.0 : 0.0,
                              // 应用内顶栏即唯一标题栏：中部标题区按下即拖（task_12 D2：
                              // onPanStart 有位移斜率门槛且错过 GTK 隐式抓取时机，拖动失效；
                              // 改为 onPointerDown 立即 beginDrag），双击切换最大化
                              child: Container(
                                height: 44.0,
                                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                                decoration: BoxDecoration(
                                  color: surfaceBg.withOpacity(0.92),
                                  border: Border(bottom: BorderSide(color: borderColor, width: 0.5)),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
                                      children: [
                                        // 返回独立书库 (将文件控制和阅读彻底解耦)
                                        IconButton(
                                          tooltip: '返回书库 (文件管理)',
                                          icon: Icon(Icons.arrow_back_ios_new, size: 15.0, color: textSecondary),
                                          onPressed: widget.onBackToLibrary,
                                        ),
                                        const SizedBox(width: 4.0),
                                        IconButton(
                                          tooltip: '文章罗盘/目录 (Cmd+\\)',
                                          icon: Icon(
                                            _isTocOpen ? Icons.menu_open : Icons.menu,
                                            size: 18.0,
                                            color: _isTocOpen ? accentColor : textSecondary,
                                          ),
                                          onPressed: () => setState(() => _isTocOpen = !_isTocOpen),
                                        ),
                                      ],
                                    ),
                                    Expanded(
                                      child: GestureDetector(
                                        onDoubleTap: toggleWindowMaximize,
                                        child: Listener(
                                          behavior: HitTestBehavior.translucent,
                                          onPointerDown: (_) => WindowChannel.beginDrag(),
                                          child: Center(
                                            child: Text(
                                              _currentBookTitle,
                                              style: TextStyle(
                                                fontSize: 13.0,
                                                color: textSecondary,
                                                fontWeight: FontWeight.w500,
                                                letterSpacing: 0.2,
                                              ),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                    Row(
                                      children: [
                                        TextButton.icon(
                                          onPressed: () => _focusController.toggleFocusMode(
                                            currentVisibleParagraphId: _paragraphs.isNotEmpty ? _paragraphs.first['id'] : null,
                                          ),
                                          icon: Icon(
                                            Icons.center_focus_strong,
                                            size: 14.0,
                                            color: _focusController.isFocusModeEnabled ? accentColor : textSecondary,
                                          ),
                                          label: Text(
                                            '聚焦 (Cmd+D)',
                                            style: TextStyle(
                                              fontSize: 12.0,
                                              color: _focusController.isFocusModeEnabled ? accentColor : textSecondary,
                                            ),
                                          ),
                                        ),
                                        IconButton(
                                          tooltip: '切换日夜模式',
                                          icon: Icon(
                                            isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                                            size: 18.0,
                                            color: textSecondary,
                                          ),
                                          onPressed: widget.onToggleTheme,
                                        ),
                                        IconButton(
                                          tooltip: 'AI 认知伴读',
                                          icon: Icon(
                                            Icons.psychology_outlined,
                                            size: 18.0,
                                            color: _focusController.isCompanionDrawerOpen ? accentColor : textSecondary,
                                          ),
                                          onPressed: () {
                                            _focusController.setCompanionDrawerOpen(!_focusController.isCompanionDrawerOpen);
                                          },
                                        ),
                                        const SizedBox(width: 4.0),
                                        WindowControls(color: textSecondary),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),

                          // 2. 主沉浸阅读区
                          Expanded(
                            child: Row(
                              children: [
                                // 中央沉浸黄金阅读区 (700px 定宽，iA Writer 极致排版)
                                Expanded(
                                  child: Center(
                                    child: ConstrainedBox(
                                      constraints: const BoxConstraints(
                                        maxWidth: ReaderTheme.readingGoldenWidth,
                                      ),
                                      child: Listener(
                                        behavior: HitTestBehavior.translucent,
                                        // 记录指针轨迹：胶囊跟随鼠标位置锚定（task_12 D1）
                                        onPointerDown: (e) => _lastPointerGlobal = e.position,
                                        onPointerMove: (e) => _lastPointerGlobal = e.position,
                                        onPointerUp: (e) => _lastPointerGlobal = e.position,
                                        child: ListView.builder(
                                        controller: _scrollController,
                                        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 56.0),
                                        itemCount: _paragraphs.length + 1,
                                        itemBuilder: (context, index) {
                                          if (index == 0) {
                                            return Padding(
                                              padding: const EdgeInsets.only(bottom: 48.0),
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    _currentBookTitle,
                                                    style: const TextStyle(
                                                      fontSize: 30.0,
                                                      fontWeight: FontWeight.w600,
                                                      letterSpacing: -0.6,
                                                      height: 1.25,
                                                    ),
                                                  ),
                                                  const SizedBox(height: 12.0),
                                                  Text(
                                                    '极简主义排版 · iA Writer Typography · 纯净阅读心流',
                                                    style: TextStyle(
                                                      fontSize: 13.0,
                                                      color: textSecondary,
                                                      letterSpacing: 0.2,
                                                    ),
                                                  ),
                                                  const SizedBox(height: 28.0),
                                                  Divider(height: 1.0, color: borderColor),
                                                ],
                                              ),
                                            );
                                          }

                                          final p = _paragraphs[index - 1];
                                          final pId = p['id'] as String;
                                          final text = p['text'] as String;
                                          final paraKey = _paraKeys.putIfAbsent(
                                              pId, () => GlobalKey(debugLabel: 'para_$pId'));
                                          final opacity = _focusController.getParagraphOpacity(pId);
                                          // 选区级内联高亮（task_12 D5）：该段落全部区间标注
                                          final paragraphRanges = _annotations
                                              .where((a) => a.paragraphId == pId && a.hasRange)
                                              .map((a) => AnnotationRange(
                                                    start: a.startOffset!,
                                                    end: a.endOffset!,
                                                    style: AnnotationStyle.highlight,
                                                    color: annotationColorFromHex(a.colorHex)
                                                        .withOpacity(0.35),
                                                  ))
                                              .toList();
                                          final paragraphSpan = AnnotationSpanBuilder.build(
                                            text: text,
                                            ranges: paragraphRanges,
                                            baseStyle: Theme.of(context).textTheme.bodyLarge,
                                          );
                                          final notes = _annotations
                                              .where((a) =>
                                                  a.paragraphId == pId &&
                                                  (a.noteText?.isNotEmpty ?? false))
                                              .toList();

                                          return AnimatedOpacity(
                                            duration: ReaderTheme.focusTransitionDuration,
                                            opacity: opacity,
                                            child: Container(
                                              key: paraKey,
                                              margin: const EdgeInsets.only(bottom: ReaderTheme.paragraphSpacing),
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  SelectableText.rich(
                                                    paragraphSpan,
                                                    onSelectionChanged: (selection, cause) {
                                                      if (!selection.isCollapsed) {
                                                        final selectedStr = selection.textInside(text);
                                                        if (selectedStr.length >= 2) {
                                                          setState(() {
                                                            _selectedTextCache = selectedStr;
                                                            _selectedParagraphIdCache = pId;
                                                            _selStartCache = selection.start;
                                                            _selEndCache = selection.end;
                                                            // 胶囊跟随鼠标位置；键盘/程序化选择回退选区末矩形
                                                            _selectionPosition =
                                                                _lastPointerGlobal != null
                                                                    ? anchorPillAtPointer(
                                                                        _lastPointerGlobal!,
                                                                        MediaQuery.of(context).size)
                                                                    : _computePillPosition(pId, selection);
                                                          });
                                                        }
                                                      } else if (_selectionPosition != null) {
                                                        // 在本文内点击收起选区时同步收起胶囊
                                                        setState(() {
                                                          _selectionPosition = null;
                                                          _selStartCache = null;
                                                          _selEndCache = null;
                                                        });
                                                      }
                                                    },
                                                  ),
                                                  if (notes != null && notes.isNotEmpty)
                                                    Padding(
                                                      padding: const EdgeInsets.only(top: 8.0),
                                                      child: Row(
                                                        children: [
                                                          Icon(Icons.bookmark_border, size: 14.0, color: accentColor),
                                                          const SizedBox(width: 4.0),
                                                          Text(
                                                            '${notes.length} 条已存边注',
                                                            style: TextStyle(fontSize: 11.5, color: accentColor, fontWeight: FontWeight.w500),
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                ],
                                              ),
                                            ),
                                          );
                                        },
                                      ),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),

                      // 毛玻璃弹窗层：文章导航（目录/导图/词云）
                      if (isDesktop && _isTocOpen)
                        Positioned.fill(
                          child: FrostedModal(
                            width: 360.0,
                            maxHeight: 620.0,
                            onDismiss: () => setState(() => _isTocOpen = false),
                            child: SizedBox(
                              height: 620.0,
                              child: TocMindmapDrawer(
                                sections: _tocSections,
                                mindmapNodes: _mindmapNodes,
                                keywords: _keywords,
                                activeSectionId: _activeSectionId,
                                onClose: () => setState(() => _isTocOpen = false),
                                onSectionSelected: (sec) {
                                  setState(() => _activeSectionId = sec.id);
                                },
                                onKeywordSelected: (kw) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('已锚定核心概念：#$kw'), duration: const Duration(milliseconds: 1200)),
                                  );
                                },
                              ),
                            ),
                          ),
                        ),

                      // 毛玻璃弹窗层：AI 认知伴读
                      if (isDesktop && _focusController.isCompanionDrawerOpen)
                        Positioned.fill(
                          child: FrostedModal(
                            width: 440.0,
                            maxHeight: 600.0,
                            onDismiss: () {
                              _focusController.setCompanionDrawerOpen(false);
                              _focusController.exitFocusMode();
                            },
                            child: SizedBox(
                              height: 560.0,
                              child: CompanionDrawer(
                                selectedText: _focusController.selectedText ?? _selectedTextCache ?? '',
                                currentTemplate: _activeTemplate,
                                initialAnalysis: _activeAnalysisText,
                                offlineMode: _companionOffline,
                                onOpenSettings: () => LlmSettingsDialog.show(context, widget.bridge),
                                onClose: () {
                                  _focusController.setCompanionDrawerOpen(false);
                                  _focusController.exitFocusMode();
                                },
                                onSaveAnnotation: (note) async {
                                  final targetPid = _focusController.activeParagraphId ?? 'p1';
                                  final para = _paragraphs.firstWhere(
                                    (p) => p['id'] == targetPid,
                                    orElse: () => {'section_id': _activeSectionId},
                                  );
                                  final res = await widget.bridge.invoke('annotation.save', {
                                    'book_id': _currentBookId,
                                    'section_id': (para['section_id'] as int?) ?? _activeSectionId,
                                    'paragraph_id': targetPid,
                                    'style': 'margin_note',
                                    'note_text': note,
                                    'color': '#007AFF',
                                  });
                                  if (!mounted) return;
                                  setState(() {
                                    _annotations.add(AnnotationItem(
                                      id: res.data['annotation_id']?.toString() ?? '',
                                      bookId: _currentBookId,
                                      sectionId: _activeSectionId,
                                      paragraphId: targetPid,
                                      style: AnnotationStyle.marginNote,
                                      colorHex: '#007AFF',
                                      noteText: note,
                                    ));
                                  });
                                },
                                onAskFollowUp: (q) async {
                                  final res = await widget.bridge.invoke('ai.companion_ask', {
                                    'book_id': _currentBookId,
                                    'template_type': _activeTemplate.templateKey,
                                    'selected_text': _focusController.selectedText ?? '',
                                    'prompt': q,
                                  });
                                  final answer =
                                      (res.data['analysis'] ?? res.data['response'] ?? '追问分析完成') as String;
                                  if (mounted) {
                                    setState(() => _companionOffline = answer.startsWith('【离线模式】'));
                                  }
                                  return answer;
                                },
                              ),
                            ),
                          ),
                        ),

                      // 划词快速伴读悬浮胶囊 (DESIGN.md §4.2: 5 按钮；锚定鼠标位置，点外部即收)
                      if (_selectionPosition != null)
                        Positioned(
                          top: _selectionPosition!.dy,
                          left: _selectionPosition!.dx,
                          child: TapRegion(
                            onTapOutside: (_) {
                              if (_selectionPosition != null) {
                                setState(_clearSelection);
                              }
                            },
                            child: FloatingActionPill(
                              onTemplateSelected: (tpl) {
                                if (tpl == CognitiveTemplateType.highlight) {
                                  _handleHighlight();
                                } else {
                                  final text = _selectedTextCache ?? '';
                                  final pId = _selectedParagraphIdCache ?? 'p1';
                                  _triggerCompanion(pId, text, tpl);
                                }
                              },
                            ),
                          ),
                        ),

                      // 移动端伴读 Bottom Sheet (DESIGN.md §5: 半屏拖拽滑层)
                      if (!isDesktop && _focusController.isCompanionDrawerOpen)
                        MobileCompanionSheet(
                          currentTemplate: _activeTemplate,
                          analysisContent: _activeAnalysisText,
                          onDismiss: () {
                            _focusController.setCompanionDrawerOpen(false);
                            _focusController.exitFocusMode();
                          },
                          onSaveAnnotation: () async {
                            final targetPid = _focusController.activeParagraphId ?? 'p1';
                            final para = _paragraphs.firstWhere(
                              (p) => p['id'] == targetPid,
                              orElse: () => {'section_id': _activeSectionId},
                            );
                            final res = await widget.bridge.invoke('annotation.save', {
                              'book_id': _currentBookId,
                              'section_id': (para['section_id'] as int?) ?? _activeSectionId,
                              'paragraph_id': targetPid,
                              'style': 'margin_note',
                              'note_text': _activeAnalysisText,
                              'color': '#007AFF',
                            });
                            if (!mounted) return;
                            setState(() {
                              _annotations.add(AnnotationItem(
                                id: res.data['annotation_id']?.toString() ?? '',
                                bookId: _currentBookId,
                                sectionId: _activeSectionId,
                                paragraphId: targetPid,
                                style: AnnotationStyle.marginNote,
                                colorHex: '#007AFF',
                                noteText: _activeAnalysisText,
                              ));
                            });
                          },
                        ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ToggleFocusIntent extends Intent {
  const _ToggleFocusIntent();
}

class _ToggleTocIntent extends Intent {
  const _ToggleTocIntent();
}

class _ExitFocusIntent extends Intent {
  const _ExitFocusIntent();
}

class _NextParagraphIntent extends Intent {
  const _NextParagraphIntent();
}

class _PrevParagraphIntent extends Intent {
  const _PrevParagraphIntent();
}
