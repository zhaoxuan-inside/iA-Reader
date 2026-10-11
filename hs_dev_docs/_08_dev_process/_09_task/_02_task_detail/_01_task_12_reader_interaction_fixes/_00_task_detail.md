# 任务详细设计与执行记录：task_12_reader_interaction_fixes

- **任务名称**：阅读交互修复：胶囊跟随鼠标/窗口按下即拖/自绘窗口控制图标/高亮选区级持久化
- **变更分级**：`M`
- **当前状态**：`IN_PROGRESS`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T09:17:54Z`
- **最后更新**：`2026-10-11T09:30:00Z`

---

## 1. 任务背景与目标

用户实测反馈 5 个交互缺陷（附截图）：

1. 划词功能胶囊不跟随鼠标位置（现状：锚定选区末矩形，选区盒计算失败时回退段落右上角，出现胶囊远离鼠标）；
2. 窗口无法拖动（现状：`onPanStart` 需越过 ~18px 位移斜率才触发 `beginDrag`，GTK/Wayland 隐式抓取时机已不可靠）；
3. 最小化按钮显示不正确（`Icons.horizontal_rule` 13px 过细）；
4. 最大化按钮不可见（`Icons.fullscreen` 小尺寸不可辨识）；
5. 高亮一次高亮整个段落（现状：`_highlightedParagraphIds` 以段落 id 为粒度，选区 start/end offset 未记录；且仅内存态，重启丢失）。

### 设计决策

- **D1 胶囊跟随鼠标**：阅读区 `Listener` 实时记录指针全局坐标 `lastPointer`；选区完成时胶囊锚定指针上方居中（`anchorPillAtPointer` 纯函数，clamp 于窗口内）；键盘/程序化选择回退选区末矩形锚定（`anchorPillAtSelectionBox`）。纯函数落位 `features/selection_pill/domain/pill_anchor.dart` 便于单测。
- **D2 窗口按下即拖**：标题栏中部空白区（Expanded）用 `Listener.onPointerDown` 立即 `WindowChannel.beginDrag()`——GTK `begin_move_drag` 在按键仍按住的隐式抓取期内调用，X11/Wayland 均可靠；双击该区切换最大化。移除 `onPanStart` 方案；按钮区不受影响（不在拖拽区内）。书库页头部同样处理。
- **D3/D4 自绘窗口控制图标**：弃用 Material 图标字体，`CustomPaint` 线性自绘（最小化=横线、最大化=方框、还原=双方框、关闭=×），线宽 1.4 逻辑像素、14px 绘制区、32px 命中区——与 iA 纯线性语言一致且任何渲染栈下可见。
- **D5 高亮选区级 + 持久化**：新增 `AnnotationItem` 模型（id/bookId/sectionId/paragraphId/startOffset/endOffset/style/color/noteText）与 `AnnotationSpanBuilder` 纯函数（按 offset 区间构建 TextSpan 树，高亮=背景色内联）；`_handleHighlight` 用缓存选区 start/end 经 `annotation.save`（`anchor={paragraph_id,start,end,section_id}`，落库 `anchor_json`，复用现有 schema 零迁移）持久化；`annotation.list` 回填重建内联渲染。渲染从段落 Container 背景（整段）改为 `SelectableText.rich` 内联区间。
- **D6 后端补 `annotation.delete`**（软删 `is_del=1`），bridge mock 同步支持，为 task_13 标注管理铺路。

---

## 2. 验收标准

1. 划词后胶囊出现在鼠标松开位置上方居中（±容差），且 clamp 于窗口内——单测覆盖纯函数 + widget 测试覆盖端到端；
2. 顶栏标题区按下（无需位移）即触发 `beginDrag`；双击切换最大化（widget 测试验证回调通道）；
3. WindowControls 三个按钮均为自绘 CustomPaint，tooltip 齐备，无 Material Icon 依赖（单测）；
4. 高亮只作用于所选子串：widget 测试断言 RichText 中带背景色的文本恰为选区文本；`annotation.list` 含 anchor start/end；
5. 重启后 `annotation.list` 回填渲染高亮（bridge mock 内存态模拟持久化往返）；
6. 全量 `flutter test` 绿；后端 `cargo build` 通过。

---

## 3. 执行步骤 (Checklist)

- [x] 1. 完善设计文档与接口定义（本文件 + 纯函数 seam：pill_anchor / AnnotationSpanBuilder）
- [x] 2. 红灯：annotation_span_builder_test / pill_anchor_test / window_controls_test / selection_highlight_range_test
- [x] 3. 绿灯：模型与纯函数实现 + WindowControls 自绘 + main.dart 改造 + bridge mock + 后端 annotation.delete
- [x] 4. 全量测试与回归（28 passed，含既有 14 用例；goldens 因自绘图标+rich 渲染路径按流程更新）
- [x] 5. 门禁与提交

### 排障记录
- `TextStyle.merge` 方向坑：`_styleFor(r).merge(baseStyle)` 在 `baseStyle.inherit=false`（Material 3 TextTheme）时直接返回 baseStyle，丢弃标注背景色——改为 `baseStyle?.merge(_styleFor(r))`（标注样式覆盖基础样式）。
- 断言对象坑：`SelectableText` 走 `RenderEditable` 不产生 `RichText` widget；新版 Flutter 中 EditableText 的 renderObject 是 `_RenderCompositionCallback` 包装，需全树 `whereType<RenderEditable>()` 后读 `re.text`。
- Golden 0.03% 差异 = 自绘窗口图标 + rich 渲染路径亚像素差，属预期变更，`--update-goldens` 流程更新。

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
frontend/lib/features/selection_pill/domain/pill_anchor.dart         [新增] 胶囊锚定纯函数
frontend/lib/features/annotation/domain/annotation_item.dart         [新增] 标注模型 + list 行归一化
frontend/lib/features/annotation/domain/annotation_span_builder.dart [新增] 区间 TextSpan 构建
frontend/lib/core/widgets/window_controls.dart                       [修改] 自绘线性图标（最小化/最大化/还原/关闭）
frontend/lib/core/ffi/reader_engine_bridge.dart                      [修改] mock annotation save/list/delete 带 anchor/style
frontend/lib/main.dart                                               [修改] 指针跟踪/胶囊锚定/按下即拖/选区级高亮渲染/冗余 if 清理
frontend/lib/features/library/presentation/library_screen.dart       [修改] 头部标题区按下即拖+双击最大化
backend/src/ffi.rs                                                   [修改] annotation.delete 路由（storage 已有软删）
frontend/test/{annotation_span_builder,pill_anchor,window_controls,selection_highlight_range}_test.dart [新增]
frontend/test/goldens/*.png                                          [更新] 预期视觉变更
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`新增 14 用例（span builder 5 / pill anchor 5 / window controls 2 / e2e 2）全绿；全量 28 passed`
- 契约比对：`annotation.save/list/delete —— Flutter mock 与 Rust FFI 双实现对齐（anchor JSON: paragraph_id/section_id/start/end）；anchor_json 复用现有列，零 schema 迁移`
- 真机视觉验证：GNOME Wayland 截图接口受限（AccessDenied），最小化/最大化图标与按下即拖的最终视觉确认留待用户运行验收
