import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'core/theme/reader_theme.dart';
import 'core/ffi/reader_engine_bridge.dart';
import 'features/reader/presentation/controllers/focus_mode_controller.dart';
import 'features/selection_pill/presentation/floating_action_pill.dart';
import 'features/companion/presentation/companion_drawer.dart';
import 'features/mobile_sheet/presentation/mobile_companion_sheet.dart';

void main() {
  runApp(const AIReaderApp());
}

class AIReaderApp extends StatelessWidget {
  const AIReaderApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Reader',
      debugShowCheckedModeBanner: false,
      theme: ReaderTheme.lightTheme,
      darkTheme: ReaderTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const ReaderWorkbenchScreen(),
    );
  }
}

class ReaderWorkbenchScreen extends StatefulWidget {
  const ReaderWorkbenchScreen({Key? key}) : super(key: key);

  @override
  State<ReaderWorkbenchScreen> createState() => _ReaderWorkbenchScreenState();
}

class _ReaderWorkbenchScreenState extends State<ReaderWorkbenchScreen> {
  late final FocusModeController _focusController;
  late final ReaderEngineBridge _bridge;

  bool _isTocOpen = false;
  String _activeAnalysisText = '';
  CognitiveTemplateType _activeTemplate = CognitiveTemplateType.general;
  Offset? _selectionPosition;

  // 模拟文档章节段落流
  final List<Map<String, String>> _mockParagraphs = [
    {
      'id': 'p1',
      'text':
          '在现代分布式数据库设计中，写入日志（WAL）是保证原子性与持久性的关键机制。所有修改操作在落地主数据库存储介质前，必须先将日志顺序追加写入磁盘。',
    },
    {
      'id': 'p2',
      'text':
          'SQLite 在 WAL 模式下，读取者绝不阻塞写入者，写入者也绝不阻塞读取者。这极大地提升了系统的整体并发读写吞吐量。',
    },
    {
      'id': 'p3',
      'text':
          '然而在检查点（Checkpoint）执行期间，仍需协调 WAL 文件的刷新与截断，若并发事务堆积过高，可能导致单次检查点延迟抖动。',
    },
    {
      'id': 'p4',
      'text':
          '因此，认知伴读管道通过对段落 AST 进行坐标锚定与语义切片，能够实时在离线状态下提取知识拓扑与 PMI 共现关系，构建高可靠的本地知识网络。',
    },
  ];

  @override
  void initState() {
    super.initState();
    _focusController = FocusModeController();
    _bridge = ReaderEngineBridge();
  }

  @override
  void dispose() {
    _focusController.dispose();
    super.dispose();
  }

  void _triggerCompanion(String paragraphId, String text, CognitiveTemplateType template) async {
    setState(() {
      _selectionPosition = null;
      _activeTemplate = template;
      _activeAnalysisText = '正在通过本地 C-ABI 引擎分析中...';
    });
    _focusController.focusParagraph(paragraphId, selectedText: text);
    _focusController.setCompanionDrawerOpen(true);

    final res = await _bridge.invoke('ai.companion_ask', {
      'template': template.templateKey,
      'selected_text': text,
    });

    if (mounted) {
      setState(() {
        _activeAnalysisText = res.data['analysis'] ?? '解析失败';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024.0;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Shortcuts(
      shortcuts: <LogicalKeySet, Intent>{
        LogicalKeySet(LogicalKeyboardKey.meta, LogicalKeyboardKey.keyD):
            const _ToggleFocusIntent(),
        LogicalKeySet(LogicalKeyboardKey.control, LogicalKeyboardKey.keyD):
            const _ToggleFocusIntent(),
        LogicalKeySet(LogicalKeyboardKey.escape): const _ExitFocusIntent(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _ToggleFocusIntent: CallbackAction<_ToggleFocusIntent>(
            onInvoke: (_) => _focusController.toggleFocusMode(currentVisibleParagraphId: 'p2'),
          ),
          _ExitFocusIntent: CallbackAction<_ExitFocusIntent>(
            onInvoke: (_) {
              _focusController.exitFocusMode();
              _focusController.setCompanionDrawerOpen(false);
              setState(() => _selectionPosition = null);
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
                body: Stack(
                  children: [
                    Row(
                      children: [
                        // 左侧目录树 (仅桌面端展开时显现)
                        if (isDesktop && _isTocOpen)
                          Container(
                            width: 260.0,
                            decoration: BoxDecoration(
                              color: isDark
                                  ? ReaderTheme.darkBgSurface
                                  : ReaderTheme.lightBgSurface,
                              border: Border(
                                right: BorderSide(
                                  color: isDark
                                      ? ReaderTheme.darkBorderSubtle
                                      : ReaderTheme.lightBorderSubtle,
                                ),
                              ),
                            ),
                            child: ListView(
                              padding: const EdgeInsets.all(16.0),
                              children: const [
                                Text('目录 AST 与知识导图', style: TextStyle(fontWeight: FontWeight.bold)),
                                SizedBox(height: 12.0),
                                Text('- 1. 概述'),
                                Text('- 2. 存储引擎'),
                                Text('- 3. 并发控制 (当前)', style: TextStyle(color: ReaderTheme.lightAccentFocus)),
                              ],
                            ),
                          ),

                        // 中央沉浸阅读区 (定宽 700px 居中)
                        Expanded(
                          child: Center(
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(
                                maxWidth: ReaderTheme.readingGoldenWidth,
                              ),
                              child: ListView.builder(
                                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 64.0),
                                itemCount: _mockParagraphs.length,
                                itemBuilder: (context, index) {
                                  final p = _mockParagraphs[index];
                                  final opacity = _focusController.getParagraphOpacity(p['id']!);

                                  return AnimatedOpacity(
                                    duration: ReaderTheme.focusTransitionDuration,
                                    opacity: opacity,
                                    child: Padding(
                                      padding: const EdgeInsets.only(bottom: ReaderTheme.paragraphSpacing),
                                      child: SelectableText(
                                        p['text']!,
                                        style: Theme.of(context).textTheme.bodyLarge,
                                        onSelectionChanged: (selection, cause) {
                                          if (!selection.isCollapsed && selection.textInside(p['text']!).isNotEmpty) {
                                            final selectedStr = selection.textInside(p['text']!);
                                            setState(() {
                                              _selectionPosition = const Offset(200, 150);
                                            });
                                          }
                                        },
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
                        ),

                        // 右侧认知伴读抽屉 (桌面端)
                        if (isDesktop && _focusController.isCompanionDrawerOpen)
                          CompanionDrawer(
                            selectedText: _focusController.selectedText ?? '',
                            currentTemplate: _activeTemplate,
                            initialAnalysis: _activeAnalysisText,
                            onClose: () {
                              _focusController.setCompanionDrawerOpen(false);
                              _focusController.exitFocusMode();
                            },
                            onSaveAnnotation: (note) async {
                              await _bridge.invoke('annotation.save', {'note': note});
                            },
                            onAskFollowUp: (q) async {
                              final res = await _bridge.invoke('ai.companion_ask', {
                                'template': _activeTemplate.templateKey,
                                'follow_up': q,
                              });
                              return res.data['analysis'] ?? '追问成功';
                            },
                          ),
                      ],
                    ),

                    // 划词快速伴读悬浮胶囊
                    if (_selectionPosition != null)
                      Positioned(
                        top: _selectionPosition!.dy,
                        left: _selectionPosition!.dx,
                        child: FloatingActionPill(
                          onTemplateSelected: (tpl) {
                            _triggerCompanion('p2', 'SQLite 在 WAL 模式下……', tpl);
                          },
                        ),
                      ),

                    // 移动端伴读 Bottom Sheet
                    if (!isDesktop && _focusController.isCompanionDrawerOpen)
                      MobileCompanionSheet(
                        currentTemplate: _activeTemplate,
                        analysisContent: _activeAnalysisText,
                        onDismiss: () {
                          _focusController.setCompanionDrawerOpen(false);
                          _focusController.exitFocusMode();
                        },
                        onSaveAnnotation: () async {
                          await _bridge.invoke('annotation.save', {'note': _activeAnalysisText});
                        },
                      ),
                  ],
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

class _ExitFocusIntent extends Intent {
  const _ExitFocusIntent();
}
