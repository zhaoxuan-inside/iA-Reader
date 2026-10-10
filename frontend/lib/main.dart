import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'core/theme/reader_theme.dart';
import 'core/ffi/reader_engine_bridge.dart';
import 'features/reader/presentation/controllers/focus_mode_controller.dart';
import 'features/selection_pill/presentation/floating_action_pill.dart';
import 'features/companion/presentation/companion_drawer.dart';
import 'features/mobile_sheet/presentation/mobile_companion_sheet.dart';
import 'features/toc_mindmap/presentation/toc_mindmap_drawer.dart';

void main() {
  runApp(const AIReaderApp());
}

class AIReaderApp extends StatefulWidget {
  const AIReaderApp({Key? key}) : super(key: key);

  @override
  State<AIReaderApp> createState() => _AIReaderAppState();
}

class _AIReaderAppState extends State<AIReaderApp> {
  ThemeMode _themeMode = ThemeMode.dark;

  void _toggleTheme() {
    setState(() {
      _themeMode = _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Reader',
      debugShowCheckedModeBanner: false,
      theme: ReaderTheme.lightTheme,
      darkTheme: ReaderTheme.darkTheme,
      themeMode: _themeMode,
      home: ReaderWorkbenchScreen(
        onToggleTheme: _toggleTheme,
        isDarkMode: _themeMode == ThemeMode.dark,
      ),
    );
  }
}

class ReaderWorkbenchScreen extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const ReaderWorkbenchScreen({
    Key? key,
    required this.onToggleTheme,
    required this.isDarkMode,
  }) : super(key: key);

  @override
  State<ReaderWorkbenchScreen> createState() => _ReaderWorkbenchScreenState();
}

class _ReaderWorkbenchScreenState extends State<ReaderWorkbenchScreen> {
  late final FocusModeController _focusController;
  late final ReaderEngineBridge _bridge;
  final ScrollController _scrollController = ScrollController();

  // 顶栏自动淡出隐退控制 (iA Writer Immersion)
  bool _isHeaderVisible = true;
  double _lastScrollOffset = 0.0;

  // 文档状态
  int _currentBookId = 1;
  String _currentBookTitle = '分布式系统高可靠存储与认知解析';
  int _activeSectionId = 1;
  List<TocSectionItem> _tocSections = [];
  List<MindmapNodeItem> _mindmapNodes = [];
  List<KeywordTagItem> _keywords = [];
  List<Map<String, dynamic>> _paragraphs = [];
  final Set<String> _highlightedParagraphIds = {};
  final Map<String, List<String>> _paragraphAnnotations = {};

  bool _isTocOpen = true;
  String _activeAnalysisText = '';
  CognitiveTemplateType _activeTemplate = CognitiveTemplateType.general;
  Offset? _selectionPosition;
  String? _selectedTextCache;
  String? _selectedParagraphIdCache;

  @override
  void initState() {
    super.initState();
    _focusController = FocusModeController();
    _bridge = ReaderEngineBridge();

    _scrollController.addListener(_handleScroll);
    _loadDocumentData(_currentBookId);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _focusController.dispose();
    super.dispose();
  }

  void _handleScroll() {
    final offset = _scrollController.offset;
    if (offset > 60 && offset > _lastScrollOffset) {
      if (_isHeaderVisible) {
        setState(() => _isHeaderVisible = false);
      }
    } else if (offset < _lastScrollOffset || offset <= 30) {
      if (!_isHeaderVisible) {
        setState(() => _isHeaderVisible = true);
      }
    }
    _lastScrollOffset = offset;
  }

  Future<void> _loadDocumentData(int bookId) async {
    // 1. 加载文档章节与段落
    final docRes = await _bridge.invoke('doc.get', {'book_id': bookId});
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
    final mmRes = await _bridge.invoke('mindmap.generate', {'book_id': bookId});
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
    final kwRes = await _bridge.invoke('nlp.keyword_extract', {'book_id': bookId});
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

    // 4. 加载已有边注
    final annRes = await _bridge.invoke('annotation.list', {'book_id': bookId});
    if (annRes.isSuccess) {
      final anns = (annRes.data['annotations'] as List<dynamic>?) ?? [];
      final noteMap = <String, List<String>>{};
      for (final a in anns) {
        final pId = a['paragraph_id']?.toString() ?? 'p1';
        noteMap.putIfAbsent(pId, () => []).add(a['note_text'] ?? '');
      }
      setState(() => _paragraphAnnotations.addAll(noteMap));
    }
  }

  void _triggerCompanion(String paragraphId, String text, CognitiveTemplateType template) async {
    setState(() {
      _selectionPosition = null;
      _activeTemplate = template;
      _activeAnalysisText = '正在调用底层六元组计算引擎分析中...';
    });
    _focusController.focusParagraph(paragraphId, selectedText: text);
    _focusController.setCompanionDrawerOpen(true);

    final res = await _bridge.invoke('ai.companion_ask', {
      'book_id': _currentBookId,
      'template_type': template.templateKey,
      'selected_text': text,
    });

    if (mounted) {
      setState(() {
        _activeAnalysisText = res.data['analysis'] ?? res.data['response'] ?? '解析完成';
      });
    }
  }

  void _handleHighlight() {
    if (_selectedParagraphIdCache != null) {
      setState(() {
        _highlightedParagraphIds.add(_selectedParagraphIdCache!);
        _selectionPosition = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('🖍 已添加高亮标记')),
      );
    }
  }

  void _showBookSwitchDialog() async {
    final res = await _bridge.invoke('doc.list', {});
    if (!mounted) return;
    final books = (res.data['books'] as List<dynamic>?) ?? [];

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('书库与文档切换', style: TextStyle(fontSize: 16.0, fontWeight: FontWeight.bold)),
          content: SizedBox(
            width: 400.0,
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: books.length,
              separatorBuilder: (_, __) => const Divider(height: 1.0),
              itemBuilder: (_, index) {
                final b = books[index];
                final isCurrent = b['id'] == _currentBookId;
                return ListTile(
                  dense: true,
                  title: Text(
                    b['title'] ?? '未命名文档',
                    style: TextStyle(
                      fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                      color: isCurrent ? ReaderTheme.lightAccentFocus : null,
                    ),
                  ),
                  subtitle: Text('格式: ${b['format'] ?? 'MD'} · 作者: ${b['author'] ?? '未知'}'),
                  trailing: isCurrent ? const Icon(Icons.check, size: 16.0, color: ReaderTheme.lightAccentFocus) : null,
                  onTap: () {
                    Navigator.of(ctx).pop();
                    _loadDocumentData(b['id'] as int);
                  },
                );
              },
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('关闭'),
            ),
          ],
        );
      },
    );
  }

  void _showOpenFileDialog() {
    final controller = TextEditingController(text: '/path/to/sample_technical_doc.md');
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('打开本地文档 (MD / EPUB / TXT / PDF)'),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: '输入文档绝对路径',
              hintText: '如: /home/user/Documents/book.epub',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('取消'),
            ),
            ElevatedButton(
              onPressed: () async {
                final path = controller.text.trim();
                Navigator.of(ctx).pop();
                if (path.isNotEmpty) {
                  final res = await _bridge.invoke('doc.parse', {'file_path': path});
                  if (res.isSuccess) {
                    final bookId = res.data['book_id'] ?? res.data['id'] ?? 1;
                    _loadDocumentData(bookId);
                  } else {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('解析失败: ${res.message}')),
                      );
                    }
                  }
                }
              },
              child: const Text('解析并打开'),
            ),
          ],
        );
      },
    );
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

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024.0;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final canvasBg = isDark ? ReaderTheme.darkBgCanvas : ReaderTheme.lightBgCanvas;
    final surfaceBg = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;
    final highlightBg = isDark ? ReaderTheme.darkHighlightMark : ReaderTheme.lightHighlightMark;

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
              _focusController.exitFocusMode();
              _focusController.setCompanionDrawerOpen(false);
              setState(() => _selectionPosition = null);
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
                    if (e.position.dy < 48 && !_isHeaderVisible) {
                      setState(() => _isHeaderVisible = true);
                    }
                  },
                  child: Stack(
                    children: [
                      Column(
                        children: [
                          // 1. 极简自动隐退顶栏 (DESIGN.md §4.1: 44px 高度)
                          AnimatedContainer(
                            duration: ReaderTheme.chromeFadeDuration,
                            curve: Curves.easeInOut,
                            height: _isHeaderVisible ? 44.0 : 0.0,
                            child: AnimatedOpacity(
                              duration: ReaderTheme.chromeFadeDuration,
                              opacity: _isHeaderVisible ? 1.0 : 0.0,
                              child: Container(
                                height: 44.0,
                                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                                decoration: BoxDecoration(
                                  color: surfaceBg,
                                  border: Border(bottom: BorderSide(color: borderColor, width: 1.0)),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
                                      children: [
                                        if (isDesktop)
                                          IconButton(
                                            tooltip: '切换目录/导图 (Cmd+\\)',
                                            icon: Icon(Icons.menu, size: 18.0, color: textSecondary),
                                            onPressed: () => setState(() => _isTocOpen = !_isTocOpen),
                                          ),
                                        IconButton(
                                          tooltip: '打开本地文档',
                                          icon: Icon(Icons.folder_open_outlined, size: 18.0, color: textSecondary),
                                          onPressed: _showOpenFileDialog,
                                        ),
                                      ],
                                    ),
                                    Expanded(
                                      child: Center(
                                        child: Text(
                                          _currentBookTitle,
                                          style: TextStyle(
                                            fontSize: 13.0,
                                            color: textSecondary,
                                            fontWeight: FontWeight.w500,
                                          ),
                                          overflow: TextOverflow.ellipsis,
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
                                            size: 15.0,
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
                                          tooltip: '伴读抽屉',
                                          icon: Icon(
                                            Icons.psychology_outlined,
                                            size: 18.0,
                                            color: _focusController.isCompanionDrawerOpen ? accentColor : textSecondary,
                                          ),
                                          onPressed: () {
                                            _focusController.setCompanionDrawerOpen(!_focusController.isCompanionDrawerOpen);
                                          },
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),

                          // 2. 主工作区
                          Expanded(
                            child: Row(
                              children: [
                                // 左侧目录与导图 (桌面端)
                                if (isDesktop && _isTocOpen)
                                  TocMindmapDrawer(
                                    sections: _tocSections,
                                    mindmapNodes: _mindmapNodes,
                                    keywords: _keywords,
                                    activeSectionId: _activeSectionId,
                                    onSectionSelected: (sec) {
                                      setState(() => _activeSectionId = sec.id);
                                    },
                                    onKeywordSelected: (kw) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('已锚定全书核心概念：#$kw')),
                                      );
                                    },
                                    onOpenFile: _showOpenFileDialog,
                                    onSwitchBook: _showBookSwitchDialog,
                                  ),

                                // 中央沉浸黄金阅读区 (700px 定宽)
                                Expanded(
                                  child: Center(
                                    child: ConstrainedBox(
                                      constraints: const BoxConstraints(
                                        maxWidth: ReaderTheme.readingGoldenWidth,
                                      ),
                                      child: ListView.builder(
                                        controller: _scrollController,
                                        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 48.0),
                                        itemCount: _paragraphs.length + 1,
                                        itemBuilder: (context, index) {
                                          if (index == 0) {
                                            return Padding(
                                              padding: const EdgeInsets.only(bottom: 36.0),
                                              child: Column(
                                                crossAxisAlignment: CrossCrossAlignment.start,
                                                children: [
                                                  Text(
                                                    _currentBookTitle,
                                                    style: const TextStyle(
                                                      fontSize: 28.0,
                                                      fontWeight: FontWeight.bold,
                                                      letterSpacing: -0.5,
                                                    ),
                                                  ),
                                                  const SizedBox(height: 8.0),
                                                  Text(
                                                    '极简主义排版 · iA Writer Typography · 本地优先离线计算',
                                                    style: TextStyle(fontSize: 13.0, color: textSecondary),
                                                  ),
                                                  const SizedBox(height: 24.0),
                                                  const Divider(height: 1.0),
                                                ],
                                              ),
                                            );
                                          }

                                          final p = _paragraphs[index - 1];
                                          final pId = p['id'] as String;
                                          final text = p['text'] as String;
                                          final opacity = _focusController.getParagraphOpacity(pId);
                                          final isHighlighted = _highlightedParagraphIds.contains(pId);
                                          final notes = _paragraphAnnotations[pId];

                                          return AnimatedOpacity(
                                            duration: ReaderTheme.focusTransitionDuration,
                                            opacity: opacity,
                                            child: Container(
                                              margin: const EdgeInsets.only(bottom: ReaderTheme.paragraphSpacing),
                                              padding: isHighlighted
                                                  ? const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0)
                                                  : EdgeInsets.zero,
                                              decoration: isHighlighted
                                                  ? BoxDecoration(
                                                      color: highlightBg,
                                                      borderRadius: BorderRadius.circular(4.0),
                                                    )
                                                  : null,
                                              child: Column(
                                                crossAxisAlignment: CrossCrossAlignment.start,
                                                children: [
                                                  SelectableText(
                                                    text,
                                                    style: Theme.of(context).textTheme.bodyLarge,
                                                    onSelectionChanged: (selection, cause) {
                                                      if (!selection.isCollapsed) {
                                                        final selectedStr = selection.textInside(text);
                                                        if (selectedStr.length >= 2) {
                                                          setState(() {
                                                            _selectedTextCache = selectedStr;
                                                            _selectedParagraphIdCache = pId;
                                                            _selectionPosition = const Offset(260.0, 180.0);
                                                          });
                                                        }
                                                      }
                                                    },
                                                  ),
                                                  if (notes != null && notes.isNotEmpty)
                                                    Padding(
                                                      padding: const EdgeInsets.only(top: 6.0),
                                                      child: Row(
                                                        children: [
                                                          Icon(Icons.bookmark, size: 14.0, color: accentColor),
                                                          const SizedBox(width: 4.0),
                                                          Text(
                                                            '${notes.length} 条已存边注',
                                                            style: TextStyle(fontSize: 11.0, color: accentColor),
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

                                // 右侧认知伴读抽屉 (桌面端 380px)
                                if (isDesktop && _focusController.isCompanionDrawerOpen)
                                  CompanionDrawer(
                                    selectedText: _focusController.selectedText ?? _selectedTextCache ?? '',
                                    currentTemplate: _activeTemplate,
                                    initialAnalysis: _activeAnalysisText,
                                    onClose: () {
                                      _focusController.setCompanionDrawerOpen(false);
                                      _focusController.exitFocusMode();
                                    },
                                    onSaveAnnotation: (note) async {
                                      final targetPid = _focusController.activeParagraphId ?? 'p1';
                                      await _bridge.invoke('annotation.save', {
                                        'book_id': _currentBookId,
                                        'section_id': _activeSectionId,
                                        'paragraph_id': targetPid,
                                        'note_text': note,
                                        'color': '#007AFF',
                                      });
                                      setState(() {
                                        _paragraphAnnotations.putIfAbsent(targetPid, () => []).add(note);
                                      });
                                    },
                                    onAskFollowUp: (q) async {
                                      final res = await _bridge.invoke('ai.companion_ask', {
                                        'book_id': _currentBookId,
                                        'template_type': _activeTemplate.templateKey,
                                        'selected_text': _focusController.selectedText ?? '',
                                        'prompt': q,
                                      });
                                      return res.data['analysis'] ?? res.data['response'] ?? '追问分析完成';
                                    },
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),

                      // 划词快速伴读悬浮胶囊 (DESIGN.md §4.2: 5 按钮)
                      if (_selectionPosition != null)
                        Positioned(
                          top: _selectionPosition!.dy,
                          left: _selectionPosition!.dx,
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
                            await _bridge.invoke('annotation.save', {
                              'book_id': _currentBookId,
                              'section_id': _activeSectionId,
                              'paragraph_id': targetPid,
                              'note_text': _activeAnalysisText,
                              'color': '#007AFF',
                            });
                            setState(() {
                              _paragraphAnnotations.putIfAbsent(targetPid, () => []).add(_activeAnalysisText);
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
