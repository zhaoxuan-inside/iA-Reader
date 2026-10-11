# 任务详细设计与执行记录：task_16_annotation_edit_mindmap_jump

- **任务名称**：清零遗留①——批注可编辑（annotation.update 全链）+ 导图节点联动章节跳转
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：agent
- **开始时间**：`2026-10-11T19:05:00Z`

---

## 1. 任务背景与目标

task_13~15 收尾时登记的两项遗留：①标注管理器对批注只能删除不能编辑；②导图节点点击只弹 SnackBar 未联动章节跳转。本任务清零。

### 设计决策

- **D1 批注编辑后端**：新增 `annotation.update` action——`storage.update_annotation(id, note_text/color/style 三字段 COALESCE 部分更新 + version+1)`；mock 同步。
- **D2 编辑交互**：管理器中带批注文本的行加「编辑」按钮 → 复用 NoteEditorPopover（initialText 预填）→ 保存走 update；main 以 `_editingAnnotationId` 区分新建/编辑。
- **D3 导图联动**：后端 `MindmapNode.section_id` 本就存在——前端 `MindmapNodeItem` 补解析 `section_id`（mock 节点同步补齐），`MindmapCanvas.onNodeSelected` 升级为回调整节点；main 收到 sectionId → 关闭目录弹窗 + 设 activeSectionId + `animateTo` 滚动到该章节首段（paraKey RenderBox 全局坐标换算滚动目标，clamp 0..maxExtent）；无 sectionId（概念节点）保持 SnackBar 定位。

---

## 2. 验收标准

1. cargo：update_annotation 持久化往返（save→update→get 断言）+ 软删行不可更新；
2. dart：mock `annotation.update` 往返；管理器行出现编辑入口且回调携带 id 与原文；
3. 带章节关联的导图节点点击回调携带 sectionId；mock 节点齐全；
4. 全量 flutter test 绿 + cargo test 绿。

---

## 3. 执行步骤 (Checklist)

- [x] 1. 后端 update_annotation + ffi action + cargo 测试
- [x] 2. mock annotation.update + MindmapNodeItem.sectionId
- [x] 3. 管理器编辑入口 + NoteEditorPopover 复用 + main 编辑流
- [x] 4. 导图 sectionId 解析 + _jumpToSection + 画布回调整节点
- [x] 5. 全量回归（56 passed）+ 提交

### 排障记录
- **Stack 层级 bug**：批注编辑浮层原排在管理器弹窗之前，从管理器点「编辑」后编辑器被压在管理器 ListView 之下不可达（hit test 实证）——编辑浮层移至 Stack 末尾（最高层级）。
- **测试隔离 bug**：ReaderEngineBridge 是单例工厂，内存 mock 标注跨同进程用例共享造成顺序依赖（首条批注计数 '1 条批注' vs 上一用例残留 '2 条批注'）——新增 `resetMockStateForTest()`，三个 e2e harness pump 前调用。

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
backend/src/storage.rs / ffi.rs            [修改] update_annotation + action
frontend/lib/core/ffi/reader_engine_bridge.dart [修改] mock update + mindmap 节点 section_id
frontend/lib/features/annotation/presentation/annotation_manager.dart [修改] 编辑入口
frontend/lib/features/annotation/presentation/note_editor_popover.dart [不变] 已支持 initialText
frontend/lib/features/toc_mindmap/presentation/toc_mindmap_drawer.dart [修改] onNodeSelected 整节点回调
frontend/lib/features/toc_mindmap/presentation/mindmap_canvas.dart [修改] 回调整节点
frontend/lib/main.dart                     [修改] 编辑流 + _jumpToSection
backend tests / frontend tests             [修改/新增]
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`cargo +1（update 往返/软删守卫）；flutter +3（节点 sectionId 回调/管理器编辑/update mock 往返）；全量 56 passed`
