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

/// 左侧纯粹目录与导图悬浮抽屉 (TocMindmapDrawer)
/// 严格对标 iA Writer 设计哲学：
/// 1. 彻底移除书库切换、文件导入等文件系统管理杂项；
/// 2. 仅作为“当前文章的导航罗盘”；
/// 3. 提供极简 260px 宽度、轻量双 Tab（章节 AST / 导图与词云），阅毕即退。
class TocMindmapDrawer extends StatefulWidget {
  final List<TocSectionItem> sections;
  final List<MindmapNodeItem> mindmapNodes;
  final List<KeywordTagItem> keywords;
  final int activeSectionId;
  final Function(TocSectionItem section) onSectionSelected;
  final Function(String keyword) onKeywordSelected;
  final VoidCallback? onClose;

  const TocMindmapDrawer({
    Key? key,
    required this.sections,
    required this.mindmapNodes,
    required this.keywords,
    required this.activeSectionId,
    required this.onSectionSelected,
    required this.onKeywordSelected,
    this.onClose,
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
        border: Border(right: BorderSide(color: borderColor, width: 0.5)),
      ),
      child: Column(
        children: [
          // 极简顶部标题与收起按钮 (无文件管理杂项)
          Container(
            height: 44.0,
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: borderColor, width: 0.5)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '文章导航',
                  style: TextStyle(
                    fontSize: 12.0,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                    color: textSecondary,
                  ),
                ),
                if (widget.onClose != null)
                  IconButton(
                    icon: Icon(Icons.close, size: 16.0, color: textSecondary),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    tooltip: '收起导航 (Esc / Cmd+\\)',
                    onPressed: widget.onClose,
                  ),
              ],
            ),
          ),

          // 双 Tab 栏 (极简无噪)
          TabBar(
            controller: _tabController,
            labelColor: accentColor,
            unselectedLabelColor: textSecondary,
            indicatorColor: accentColor,
            indicatorWeight: 1.5,
            indicatorSize: TabBarIndicatorSize.tab,
            labelStyle: const TextStyle(fontSize: 12.0, fontWeight: FontWeight.w600),
            tabs: const [
              Tab(text: '章节 AST 目录'),
              Tab(text: '知识导图 & 词云'),
            ],
          ),

          Divider(height: 0.5, color: borderColor),

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
                              width: 2.5,
                            ),
                          ),
                        ),
                        child: Text(
                          sec.title,
                          style: TextStyle(
                            fontSize: 13.0,
                            fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                            color: isActive ? accentColor : textPrimary,
                            height: 1.4,
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
                      '核心概念词云',
                      style: TextStyle(
                        fontSize: 11.5,
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
                            padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 3.5),
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
                        fontSize: 11.5,
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
                              size: node.depth == 0 ? 7.0 : 11.0,
                              color: node.depth == 0 ? accentColor : textSecondary,
                            ),
                            const SizedBox(width: 6.0),
                            Expanded(
                              child: Text(
                                node.label,
                                style: TextStyle(
                                  fontSize: 12.0,
                                  fontWeight: node.depth == 0 ? FontWeight.w600 : FontWeight.normal,
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
