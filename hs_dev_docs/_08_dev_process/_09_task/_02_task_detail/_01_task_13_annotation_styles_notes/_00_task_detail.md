# 任务详细设计与执行记录：task_13_annotation_styles_notes

- **任务名称**：标注系统升级——样式分类（下划线/波浪线/加粗/斜体/删除线/半高亮×调色板）+ 人工批注 + 标注管理
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T17:52:00Z`
- **最后更新**：`2026-10-11T10:00:03Z`

---

## 1. 任务背景与目标

用户需求（#7/#8）：需要更多内容标注方式——下划线、波浪线、加粗、斜体、删除线、只高亮一半文字、高亮颜色可选、功能分类；需要人工批注功能。

### 设计决策

- **D1 样式分类**：`AnnotationStyle` 扩展为 `highlight / halfHighlight / underline / wavy / strike / bold / italic / marginNote`，分组：背景类（高亮/半高亮）、线条类（下划线/波浪线/删除线）、字型类（加粗/斜体）、批注类。半高亮用 `TextDecoration.underline + thickness≈0.42em + decorationColor 55% alpha` 模拟下半高亮（TextSpan 无半高背景能力）。
- **D2 调色板**：6 色固定 `annotationColorPalette`（琥珀/蓝/绿/红/紫/灰），默认琥珀 `#CA8A04`；颜色随标注落库 `color` 字段，渲染时按样式叠加透明度。
- **D3 标注面板**：胶囊新增第 6 按钮「标注」（保留原 5 按钮与 task_12 行为，高亮=默认琥珀直通车），点「标注」在胶囊位置展开 `AnnotationPalette`：分组样式按钮行 + 颜色行 + 「批注」入口；点样式即应用当前选区并收起。
- **D4 人工批注**：面板「批注」→ `NoteEditorPopover`（FrostedModal 复用）多行输入 → `margin_note` 样式保存（anchor 带选区区间 + note_text）→ 段落下方「n 条批注」行。
- **D5 标注管理**：`AnnotationManagerModal`（FrostedModal 440px）列出全书标注：样式名 + 色点 + 摘录 + 批注文本 + 删除（`annotation.delete`）。
- **D6 点击标注区间**：SelectableText 外层 `GestureDetector.onTapUp` → `RenderParagraph.getPositionForOffset` → 命中任一区间即打开管理器。
- **D7 复用后端**：style 为自由字符串、color/anchor_json 已就绪，后端零改动。

---

## 2. 验收标准

1. 七种样式渲染正确：builder 单测断言每种样式的 TextStyle（背景/装饰线型/线宽/字重/斜体），半高亮厚度随 baseStyle.fontSize 缩放；
2. 调色板 6 色可选且落库 colorHex；面板分类清晰（背景/线条/字型/批注）；
3. 人工批注：选区 → 批注 → 输入 → 保存 → 段落计数行出现，bridge `annotation.list` 含 note_text 与区间 anchor；
4. 管理器：列出全书标注、点击标注区间可打开、可删除（mock 往返验证）；
5. 全量 flutter test 绿；后端无改动即兼容。

---

## 3. 执行步骤 (Checklist)

- [x] 1. 详设与 seam 确认（本文件）
- [x] 2. 红灯：annotation_item_test / span builder 样式用例扩展 / annotation_palette_test / annotation_notes_e2e_test
- [x] 3. 绿灯：样式枚举与渲染映射 + 调色板 + 面板 + 批注编辑浮层 + 管理器 + main.dart 接线 + 胶囊第 6 按钮
- [x] 4. 全量回归（42 passed）
- [x] 5. 门禁与提交

### 排障与补充决策
- **D8 禁用系统选择工具栏**：SelectableText 默认 context menu（全选/拷贝）浮层与划词胶囊/标注面板同区叠加互相遮挡（hit test 实证命中的是 "Select all" 按钮）——阅读段落 `contextMenuBuilder: null`，复制走 Ctrl+C，符合 iA 极简。
- 高亮透明度统一收进 builder（调用方不再自行 withOpacity）。

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
frontend/lib/features/annotation/domain/annotation_item.dart          [修改] 样式枚举扩展 + 调色板
frontend/lib/features/annotation/domain/annotation_span_builder.dart  [修改] 全样式渲染映射（含半高亮厚度）
frontend/lib/features/annotation/presentation/annotation_palette.dart [新增] 标注面板（分类样式+颜色+批注入口）
frontend/lib/features/annotation/presentation/note_editor_popover.dart [新增] 批注编辑浮层
frontend/lib/features/annotation/presentation/annotation_manager.dart [新增] 标注管理弹窗
frontend/lib/features/selection_pill/presentation/floating_action_pill.dart [修改] 第 6 按钮「标注」
frontend/lib/main.dart                                                [修改] 面板/批注/管理器状态与接线 + 点击区间检测
frontend/test/...                                                     [新增/修改] 对应测试
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`新增 10 用例（item 4 / builder 样式 6 / palette 1 / e2e 3）；全量 42 passed`
- 契约比对：`style/color/anchor_json/note_text 全链路复用 task_12 契约，后端零改动`
