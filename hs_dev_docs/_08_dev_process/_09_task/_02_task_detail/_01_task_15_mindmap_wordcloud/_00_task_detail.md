# 任务详细设计与执行记录：task_15_mindmap_wordcloud

- **任务名称**：图形化知识导图画布（树布局/贝塞尔连线/缩放点选）+ 权重词云
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T18:40:00Z`
- **最后更新**：`2026-10-11T10:09:55Z`

---

## 1. 任务背景与目标

用户需求（#9/#10）：知识导图功能、词云功能。现状抽屉 Tab2 只有缩进文本树与均一字号词条 Wrap，无图形化导图、无权重视觉。

### 设计决策

- **D1 导图画布**：`layoutMindmapTree` 纯函数（ tidy tree：叶子按序占行、父节点 y=子节点均值、x=depth 步进，环防护）+ `MindmapCanvas`（CustomPaint 绘制贝塞尔连线与圆角节点，InteractiveViewer 缩放平移，onTapUp 命中节点回调）。节点 132×34，横向布局适配 360px 抽屉 + 缩放。
- **D2 权重词云**：`cloudFontSizeForScore`（11 + score×15，clamp）纯函数 + `WordCloud` Wrap：字号随 score、颜色强度随 score、`×count` 计数徽标，iA 单色系。
- **D3 抽屉重构**：双 Tab → 三 Tab：目录 / 知识导图（画布）/ 词云；移除缩进文本树（被画布取代）。
- **D4 交互**：点节点 → `onNodeSelected(label)` → 主界面 SnackBar 定位概念；点词 → 既有 onKeywordSelected。后端 mindmap.generate / nlp.keyword_extract 契约零改动。

---

## 2. 验收标准

1. 布局纯函数：链式树 x 随深度步进、叶子 y 顺序占行、父 y=子均值、双根与环输入安全；
2. 词云字号随 score 单调且有界；高分词明显大于低分词；
3. 画布渲染节点与连线（CustomPaint），点击节点回调命中；
4. 抽屉三 Tab 切换正常；全量测试绿。

---

## 3. 执行步骤 (Checklist)

- [x] 1. 详设（本文件）
- [x] 2. 红灯：mindmap_canvas_test（布局/字号/画布/抽屉三 Tab）
- [x] 3. 绿灯：布局+画布+词云+抽屉重构+main 接线
- [x] 4. 全量回归（54 passed）+ 提交

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
frontend/lib/features/toc_mindmap/presentation/mindmap_canvas.dart [新增] 布局纯函数+画布
frontend/lib/features/toc_mindmap/presentation/word_cloud.dart     [新增] 权重词云
frontend/lib/features/toc_mindmap/presentation/toc_mindmap_drawer.dart [修改] 三 Tab 重构
frontend/lib/main.dart                                             [修改] onNodeSelected 接线
frontend/test/mindmap_canvas_test.dart                             [新增]
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`新增 7 用例（布局 4 / 字号 1 / 画布 1 / 抽屉 1）；全量 54 passed`
- 排障记录：环引用防护需在下钻前判断（in-progress 集），positions 判断晚于递归会栈溢出；tidy tree 单叶链同行属正确语义
- 契约比对：`复用 mindmap.generate / nlp.keyword_extract，零改动`
