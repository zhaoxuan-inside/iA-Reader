import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';
import '../../../core/ffi/reader_engine_bridge.dart';
import '../../../core/widgets/window_controls.dart';
import '../../../core/window/window_channel.dart';
import '../../settings/presentation/settings_dialog.dart';

/// 极简书目模型
class LibraryBookItem {
  final int id;
  final String title;
  final String author;
  final String format;
  final int totalPages;
  final int sectionsCount;
  /// 阅读进度（0~1）：>0 时书架行展示百分比（FEAT-001 REQ-005）
  final double readProgress;

  const LibraryBookItem({
    required this.id,
    required this.title,
    required this.author,
    required this.format,
    required this.totalPages,
    required this.sectionsCount,
    this.readProgress = 0.0,
  });

  factory LibraryBookItem.fromJson(Map<String, dynamic> json) {
    return LibraryBookItem(
      id: json['id'] as int? ?? 1,
      title: json['title'] as String? ?? '未命名文档',
      author: json['author'] as String? ?? '未知作者',
      format: (json['format'] as String? ?? 'md').toUpperCase(),
      totalPages: json['total_pages'] as int? ?? 1,
      sectionsCount: json['sections_count'] as int? ?? 1,
      readProgress: (json['read_progress'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// 独立文件库与书架视图 (LibraryScreen)
/// 对标 iA Writer 经典的文件库模式 (Library Mode):
/// 1. 专注且克制的文件浏览与组织，不干扰阅读视图；
/// 2. 支持导入本地文档 (MD / TXT，MVP 冻结范围；PDF/EPUB 于 Phase 2 接入)；
/// 3. 点击书籍即刻切换进入沉浸阅读世界 (Pure Reader Mode)。
class LibraryScreen extends StatefulWidget {
  final ReaderEngineBridge bridge;
  final Function(int bookId) onOpenBook;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const LibraryScreen({
    super.key,
    required this.bridge,
    required this.onOpenBook,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  List<LibraryBookItem> _books = [];
  bool _isLoading = true;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadBooks();
  }

  Future<void> _loadBooks() async {
    setState(() => _isLoading = true);
    final res = await widget.bridge.invoke('book.list', {});
    if (res.isSuccess) {
      final list = (res.data['books'] as List<dynamic>?) ?? [];
      setState(() {
        _books = list.map((item) => LibraryBookItem.fromJson(item)).toList();
        _isLoading = false;
      });
    } else {
      setState(() => _isLoading = false);
    }
  }

  /// 删除书籍（FEAT-001 书库管理）：确认后 book.delete（引擎连带清理批注/章节等派生数据）
  void _confirmDeleteBook(LibraryBookItem book) {
    showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('删除文档', style: TextStyle(fontSize: 16.0, fontWeight: FontWeight.bold)),
          content: Text(
            '将从书库移除《${book.title}》及其批注与阅读数据。此操作不可撤销。',
            style: const TextStyle(fontSize: 13.5, height: 1.6),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('取消'),
            ),
            TextButton(
              style: TextButton.styleFrom(foregroundColor: const Color(0xFFE5484D)),
              onPressed: () async {
                Navigator.of(ctx).pop();
                await widget.bridge.invoke('book.deleted', {'book_id': book.id});
                await _loadBooks();
              },
              child: const Text('删除', style: TextStyle(fontWeight: FontWeight.w600)),
            ),
          ],
        );
      },
    );
  }

  /// 导入对话框（FEAT-001 REQ-001）：文件选择器为主入口，手输路径保留为兜底；
  /// 同内容重复导入走幂等定位——直接打开既有书目而非报错拦截
  void _showImportFileDialog() {
    final controller = TextEditingController();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setDialogState) {
          return AlertDialog(
            title: const Text('导入本地文档 (MD / TXT)',
                style: TextStyle(fontSize: 16.0, fontWeight: FontWeight.bold)),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '支持 Markdown 与纯文本；同内容文档重复导入会自动定位到书库中的既有条目。',
                  style: TextStyle(
                      fontSize: 12.0,
                      height: 1.5,
                      color: isDark ? Colors.white54 : Colors.black45),
                ),
                const SizedBox(height: 14.0),
                Row(
                  children: [
                    OutlinedButton.icon(
                      key: const Key('import_pick_file'),
                      onPressed: () async {
                        final files = await FilePicker.pickFiles(
                          type: FileType.custom,
                          allowedExtensions: const ['md', 'markdown', 'txt'],
                        );
                        final path = files.firstOrNull?.path;
                        if (path != null) {
                          setDialogState(() => controller.text = path);
                        }
                      },
                      icon: const Icon(Icons.file_open_outlined, size: 17.0),
                      label: const Text('选择文件',
                          style: TextStyle(fontSize: 13.0)),
                    ),
                    const SizedBox(width: 10.0),
                    Expanded(
                      child: Text(
                        'MD / TXT',
                        style: TextStyle(
                            fontSize: 11.5,
                            color: isDark ? Colors.white38 : Colors.black38),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12.0),
                TextField(
                  controller: controller,
                  autofocus: true,
                  decoration: const InputDecoration(
                    labelText: '或输入文档绝对路径',
                    hintText: '如: /home/user/Documents/notes.md',
                    isDense: true,
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('取消'),
              ),
              ElevatedButton(
                onPressed: () async {
                  final path = controller.text.trim();
                  if (path.isEmpty) return;
                  Navigator.of(ctx).pop();
                  await _importDocument(path);
                },
                child: const Text('导入并阅读'),
              ),
            ],
          );
        });
      },
    );
  }

  Future<void> _importDocument(String path) async {
    final res = await widget.bridge.invoke('book.parse', {'file_path': path});
    if (!mounted) return;
    if (res.isSuccess) {
      final duplicate = res.data['duplicate'] == true;
      final bookId = (res.data['id'] as num?)?.toInt() ?? 1;
      if (duplicate) {
        // 幂等定位：重复导入不是错误，直接给"打开"入口
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('该书已在书库中，已为你定位'),
            duration: const Duration(seconds: 3),
            action: SnackBarAction(
              label: '打开',
              onPressed: () => widget.onOpenBook(bookId),
            ),
          ),
        );
      } else {
        widget.onOpenBook(bookId);
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('解析失败: ${res.message}')),
      );
    }
  }

  /// 运行时未接入真实引擎（mock 通道）时向用户明示，避免把内置演示数据当真；
  /// flutter test 环境不展示，保持 golden/布局测试基线稳定
  bool get _showMockNotice =>
      widget.bridge.usesMockEngine &&
      Platform.environment['FLUTTER_TEST'] != 'true';

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDarkMode;
    final canvasBg = isDark ? ReaderTheme.darkBgCanvas : ReaderTheme.lightBgCanvas;
    final surfaceBg = isDark ? ReaderTheme.darkBgSurface : ReaderTheme.lightBgSurface;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textPrimary = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accentColor = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    final filteredBooks = _books.where((b) {
      if (_searchQuery.isEmpty) return true;
      return b.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          b.author.toLowerCase().contains(_searchQuery.toLowerCase());
    }).toList();

    return Scaffold(
      backgroundColor: canvasBg,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 极简顶部工作台控制条（应用内顶栏即唯一标题栏：标题区按下即拖 + 窗口控制）
              // task_12 D2：onPointerDown 立即 beginDrag（onPanStart 斜率门槛导致拖动失效），
              // 按钮区不在拖拽区内不受影响；双击标题区切换最大化
              Padding(
                padding: const EdgeInsets.only(left: 32.0, right: 16.0, top: 20.0, bottom: 24.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    GestureDetector(
                      onDoubleTap: toggleWindowMaximize,
                      child: Listener(
                        behavior: HitTestBehavior.translucent,
                        onPointerDown: (_) => WindowChannel.beginDrag(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'AI Reader 书库',
                              style: TextStyle(
                                fontSize: 26.0,
                                fontWeight: FontWeight.w600,
                                letterSpacing: -0.5,
                                color: textPrimary,
                              ),
                            ),
                            const SizedBox(height: 4.0),
                            Text(
                              '本地优先 · 离线认知 · 沉浸无噪',
                              style: TextStyle(
                                fontSize: 13.0,
                                color: textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                      Row(
                        children: [
                          IconButton(
                            tooltip: '伴读 LLM 设置',
                            icon: Icon(
                              Icons.settings_outlined,
                              size: 20.0,
                              color: textSecondary,
                            ),
                            onPressed: () => LlmSettingsDialog.show(context, widget.bridge),
                          ),
                          const SizedBox(width: 8.0),
                          IconButton(
                            tooltip: '切换日夜模式',
                            icon: Icon(
                              isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                              size: 20.0,
                              color: textSecondary,
                            ),
                            onPressed: widget.onToggleTheme,
                          ),
                          const SizedBox(width: 8.0),
                          TextButton.icon(
                            onPressed: _showImportFileDialog,
                            style: TextButton.styleFrom(
                              foregroundColor: accentColor,
                              padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 10.0),
                            ),
                            icon: const Icon(Icons.add, size: 18.0),
                            label: const Text('导入文档', style: TextStyle(fontSize: 13.0, fontWeight: FontWeight.w500)),
                          ),
                          const SizedBox(width: 6.0),
                          WindowControls(color: textSecondary),
                        ],
                      ),
                    ],
                  ),
              ),

              // 搜索与过滤栏
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 8.0),
                child: Container(
                  height: 42.0,
                  padding: const EdgeInsets.symmetric(horizontal: 14.0),
                  decoration: BoxDecoration(
                    color: surfaceBg,
                    borderRadius: BorderRadius.circular(8.0),
                    border: Border.all(color: borderColor, width: 0.8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.search, size: 18.0, color: textSecondary),
                      const SizedBox(width: 10.0),
                      Expanded(
                        child: TextField(
                          onChanged: (val) => setState(() => _searchQuery = val.trim()),
                          decoration: InputDecoration(
                            border: InputBorder.none,
                            hintText: '搜索文档标题或作者...',
                            hintStyle: TextStyle(fontSize: 13.0, color: textSecondary.withValues(alpha: 0.6)),
                            isDense: true,
                          ),
                          style: TextStyle(fontSize: 13.5, color: textPrimary),
                        ),
                      ),
                      if (_searchQuery.isNotEmpty)
                        GestureDetector(
                          onTap: () => setState(() => _searchQuery = ''),
                          child: Icon(Icons.clear, size: 16.0, color: textSecondary),
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16.0),

              // mock 通道明示条（运行时未加载真实引擎动态库）
              if (_showMockNotice)
                Padding(
                  padding: const EdgeInsets.only(left: 32.0, right: 32.0, bottom: 12.0),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
                    decoration: BoxDecoration(
                      color: surfaceBg,
                      borderRadius: BorderRadius.circular(8.0),
                      border: Border.all(color: borderColor, width: 0.8),
                    ),
                    child: Text(
                      '演示模式：未检测到 AI Reader 引擎动态库（libreader_core），当前展示内置示例数据。请先构建或安装原生引擎。',
                      style: TextStyle(fontSize: 12.0, color: textSecondary),
                    ),
                  ),
                ),

              // 文档列表
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator(strokeWidth: 2.0))
                    : filteredBooks.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.folder_open_outlined, size: 48.0, color: textSecondary.withValues(alpha: 0.5)),
                                const SizedBox(height: 12.0),
                                Text('暂无匹配文档，点击右上角导入本地长文', style: TextStyle(color: textSecondary, fontSize: 13.5)),
                              ],
                            ),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 12.0),
                            itemCount: filteredBooks.length,
                            separatorBuilder: (_, __) => Divider(height: 1.0, color: borderColor),
                            itemBuilder: (context, index) {
                              final book = filteredBooks[index];
                              return InkWell(
                                onTap: () => widget.onOpenBook(book.id),
                                borderRadius: BorderRadius.circular(8.0),
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 16.0),
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 36.0,
                                        height: 48.0,
                                        decoration: BoxDecoration(
                                          color: surfaceBg,
                                          borderRadius: BorderRadius.circular(4.0),
                                          border: Border.all(color: borderColor, width: 0.8),
                                        ),
                                        alignment: Alignment.center,
                                        child: Text(
                                          book.format,
                                          style: TextStyle(
                                            fontSize: 10.0,
                                            fontWeight: FontWeight.bold,
                                            color: accentColor,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 16.0),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              book.title,
                                              style: TextStyle(
                                                fontSize: 15.5,
                                                fontWeight: FontWeight.w500,
                                                color: textPrimary,
                                              ),
                                            ),
                                            const SizedBox(height: 4.0),
                                            Text(
                                              '作者: ${book.author} · ${book.sectionsCount} 个章节'
                                              '${book.readProgress > 0 ? ' · 已读 ${(book.readProgress * 100).toStringAsFixed(0)}%' : ''}',
                                              style: TextStyle(
                                                fontSize: 12.5,
                                                color: textSecondary,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Icon(Icons.arrow_forward_ios, size: 14.0, color: textSecondary.withValues(alpha: 0.4)),
                                      const SizedBox(width: 8.0),
                                      // 书库管理：删除文档（确认框防误触，见 _confirmDeleteBook）
                                      GestureDetector(
                                        onTap: () => _confirmDeleteBook(book),
                                        child: Tooltip(
                                          message: '删除文档',
                                          child: Icon(
                                            Icons.delete_outline,
                                            size: 17.0,
                                            color: textSecondary.withValues(alpha: 0.55),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
