import 'package:flutter/material.dart';
import '../../../../core/theme/reader_theme.dart';

/// 章节信息结构
class TocSectionItem {
  final int id;
  final String title;
  final String? startParagraphId;

  const TocSectionItem({
    required this.id,
    required this.title,
    this.startParagraphId,
  });
}

/// 导图节点结构
class MindmapNodeItem {
  final String id;
  final String label;
  final int depth;
  final String? parentId;

  const MindmapNodeItem({
    required this.id,
    required this.label,
    required this.depth,
    this.parentId,
  });
}

/// 核心关键词结构
class KeywordTagItem {
  final String word;
  final double score;
  final int count;

  const KeywordTagItem({
    required this.word,
    required this.score,
    required this.count,
  });
}

/// 左侧 AST 目录与知识导图抽屉 (TocMindmapDrawer)
/// 严格对标 DESIGN.md 与产品原型：260px 宽度、轻量折叠、双 Tab（目录 AST / 知识导图）
class TocMindmapDrawer extends StatefulWidget {
  final List<TocSectionItem> sections;
  final List<MindmapNodeItem> mindmapNodes;
  final List<KeywordTagItem> keywords;
  final int activeSectionId;
  final Function(TocSectionItem section) onSectionSelected;
  final Function(String keyword) onKeywordSelected;
  final VoidCallback onOpenFile;
  final VoidCallback onSwitchBook;

  const TocMindmapDrawer({
    Key? key,
    required this.sections,
    required this.mindmapNodes,
    required this.keywords,
    required this.activeSectionId,
    required this.onSectionSelected,
    required this.onKeywordSelected,
    required this.onOpenFile,
    required this.onSwitchBook,
  }) : super(key: key);

  @override
  State<TocMindmapDrawer> createState() => _TocMindmapDrawerState();
}

class _TocMindmapDrawerState extends State<TocMindmapDrawer>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
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
      width: 260.0,
      decoration: BoxDecoration(
        color: surfaceColor,
        border: Border(right: BorderSide(color: borderColor, width: 1.0)),
      ),
      child: Column(
        children: [
          // 顶部操作区：书库切换与导入
          Container(
            height: 48.0,
            padding: const EdgeInsets.symmetric(horizontal: 12.0),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: borderColor, width: 1.0)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                TextButton.icon(
                  onPressed: widget.onSwitchBook,
                  icon: Icon(Icons.auto_stories_outlined, size: 16.0, color: textSecondary),
                  label: Text(
                    '书库列表',
                    style: TextStyle(fontSize: 12.0, color: textSecondary),
                  ),
                ),
                IconButton(
                  tooltip: '导入本地文档 (MD/EPUB/TXT/PDF)',
                  icon: Icon(Icons.file_upload_outlined, size: 18.0, color: accentColor),
                  onPressed: widget.onOpenFile,
                ),
              ],
            ),
          ),

          // 双 Tab 栏
          TabBar(
            controller: _tabController,
            labelColor: accentColor,
            unselectedLabelColor: textSecondary,
            indicatorColor: accentColor,
            indicatorWeight: 2.0,
            labelStyle: const TextStyle(fontSize: 12.0, fontWeight: FontWeight.w600),
            tabs: const [
              Tab(text: '章节 AST 目录'),
              Tab(text: '知识导图 & 词云'),
            ],
          ),

          const Divider(height: 1.0),

          // 视图内容
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: 章节 AST 目录
                ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  itemCount: widget.sections.length,
                  itemBuilder: (context, index) {
                    final sec = widget.sections[index];
                    final isActive = sec.id == widget.activeSectionId;
                    return InkWell(
                      onTap: () => widget.onSectionSelected(sec),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
                        decoration: BoxDecoration(
                          color: isActive
                              ? (isDark ? const Color(0xFF27272A) : const Color(0xFFF3F4F6))
                              : Colors.transparent,
                          border: Border(
                            left: BorderSide(
                              color: isActive ? accentColor : Colors.transparent,
                              width: 3.0,
                            ),
                          ),
                        ),
                        child: Text(
                          sec.title,
                          style: TextStyle(
                            fontSize: 13.0,
                            fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                            color: isActive ? accentColor : textPrimary,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    );
                  },
                ),

                // Tab 2: 知识导图与全书核心词
                ListView(
                  padding: const EdgeInsets.all(16.0),
                  children: [
                    Text(
                      '全书核心拓扑词云',
                      style: TextStyle(
                        fontSize: 12.0,
                        fontWeight: FontWeight.w600,
                        color: textSecondary,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 10.0),
                    Wrap(
                      spacing: 6.0,
                      runSpacing: 6.0,
                      children: widget.keywords.map((kw) {
                        return InkWell(
                          onTap: () => widget.onKeywordSelected(kw.word),
                          borderRadius: BorderRadius.circular(12.0),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                            decoration: BoxDecoration(
                              color: isDark ? const Color(0xFF27272A) : const Color(0xFFF3F4F6),
                              borderRadius: BorderRadius.circular(12.0),
                              border: Border.all(color: borderColor, width: 0.5),
                            ),
                            child: Text(
                              '#${kw.word}',
                              style: TextStyle(
                                fontSize: 11.0,
                                color: kw.score > 0.8 ? accentColor : textSecondary,
                                fontWeight: kw.score > 0.8 ? FontWeight.w600 : FontWeight.normal,
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 20.0),
                    Text(
                      '结构化知识树 (Mindmap AST)',
                      style: TextStyle(
                        fontSize: 12.0,
                        fontWeight: FontWeight.w600,
                        color: textSecondary,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 10.0),
                    ...widget.mindmapNodes.map((node) {
                      final indent = node.depth * 14.0;
                      return Padding(
                        padding: EdgeInsets.only(left: indent, bottom: 8.0),
                        child: Row(
                          children: [
                            Icon(
                              node.depth == 0
                                  ? Icons.lens
                                  : (node.depth == 1 ? Icons.subdirectory_arrow_right : Icons.circle_outlined),
                              size: node.depth == 0 ? 8.0 : 12.0,
                              color: node.depth == 0 ? accentColor : textSecondary,
                            ),
                            const SizedBox(width: 6.0),
                            Expanded(
                              child: Text(
                                node.label,
                                style: TextStyle(
                                  fontSize: 12.0,
                                  fontWeight: node.depth == 0 ? FontWeight.bold : FontWeight.normal,
                                  color: textPrimary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
