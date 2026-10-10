import 'package:flutter/material.dart';
import '../../../core/theme/reader_theme.dart';
import '../../../core/ffi/reader_engine_bridge.dart';

/// 极简书目模型
class LibraryBookItem {
  final int id;
  final String title;
  final String author;
  final String format;
  final int totalPages;
  final int sectionsCount;

  const LibraryBookItem({
    required this.id,
    required this.title,
    required this.author,
    required this.format,
    required this.totalPages,
    required this.sectionsCount,
  });

  factory LibraryBookItem.fromJson(Map<String, dynamic> json) {
    return LibraryBookItem(
      id: json['id'] as int? ?? 1,
      title: json['title'] as String? ?? '未命名文档',
      author: json['author'] as String? ?? '未知作者',
      format: (json['format'] as String? ?? 'md').toUpperCase(),
      totalPages: json['total_pages'] as int? ?? 1,
      sectionsCount: json['sections_count'] as int? ?? 1,
    );
  }
}

/// 独立文件库与书架视图 (LibraryScreen)
/// 对标 iA Writer 经典的文件库模式 (Library Mode):
/// 1. 专注且克制的文件浏览与组织，不干扰阅读视图；
/// 2. 支持导入本地文档 (MD / EPUB / TXT / PDF)；
/// 3. 点击书籍即刻切换进入沉浸阅读世界 (Pure Reader Mode)。
class LibraryScreen extends StatefulWidget {
  final ReaderEngineBridge bridge;
  final Function(int bookId) onOpenBook;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const LibraryScreen({
    Key? key,
    required this.bridge,
    required this.onOpenBook,
    required this.onToggleTheme,
    required this.isDarkMode,
  }) : super(key: key);

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
    final res = await widget.bridge.invoke('doc.list', {});
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

  void _showImportFileDialog() {
    final controller = TextEditingController(text: '/path/to/sample_technical_doc.md');
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('导入本地文档 (MD / EPUB / TXT / PDF)', style: TextStyle(fontSize: 16.0, fontWeight: FontWeight.bold)),
          content: TextField(
            controller: controller,
            autofocus: true,
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
                  final res = await widget.bridge.invoke('doc.parse', {'file_path': path});
                  if (res.isSuccess) {
                    final bookId = res.data['book_id'] ?? res.data['id'] ?? 1;
                    widget.onOpenBook(bookId);
                  } else {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('解析失败: ${res.message}')),
                      );
                    }
                  }
                }
              },
              child: const Text('导入并阅读'),
            ),
          ],
        );
      },
    );
  }

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
          constraints: const BoxConstraints(maxWidth: 860.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 极简顶部工作台控制条
              Padding(
                padding: const EdgeInsets.only(left: 32.0, right: 32.0, top: 48.0, bottom: 24.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
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
                    Row(
                      children: [
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
                        ElevatedButton.icon(
                          onPressed: _showImportFileDialog,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: accentColor,
                            foregroundColor: Colors.white,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.0)),
                          ),
                          icon: const Icon(Icons.add, size: 18.0),
                          label: const Text('导入文档', style: TextStyle(fontSize: 13.0, fontWeight: FontWeight.w500)),
                        ),
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
                            hintStyle: TextStyle(fontSize: 13.0, color: textSecondary.withOpacity(0.6)),
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

              // 文档列表
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator(strokeWidth: 2.0))
                    : filteredBooks.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.folder_open_outlined, size: 48.0, color: textSecondary.withOpacity(0.5)),
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
                                              '作者: ${book.author} · ${book.sectionsCount} 个章节',
                                              style: TextStyle(
                                                fontSize: 12.5,
                                                color: textSecondary,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Icon(Icons.arrow_forward_ios, size: 14.0, color: textSecondary.withOpacity(0.4)),
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
