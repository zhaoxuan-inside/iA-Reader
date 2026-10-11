# 任务详细设计与执行记录：task_14_ai_keyboard

- **任务名称**：独立 AI 键盘面板——分类模板/伴读入口/作用域提示，Cmd+K 唤起
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T18:20:00Z`
- **最后更新**：`2026-10-11T10:04:13Z`

---

## 1. 任务背景与目标

用户需求（#6）：AI 相关的功能应该有一个单独的 AI 键盘。现状 AI 能力散落在划词胶囊（通俗/逻辑/批判/术语）与顶栏 AI 伴读按钮，缺少常驻、可发现、不依赖划词的 AI 功能面板。

### 设计决策

- **D1 形态**：底部停靠浮层（输入法键盘隐喻，非全屏 modal），圆角面板 + 发丝线边框，iA 语言零 emoji；不遮黄金版心底部以外区域。
- **D2 分区**：理解模板区（通俗/逻辑/批判/术语，文案按钮带键帽样式）+ 伴读区（「认知伴读」打开既有毛玻璃弹窗追问）+ 作用域提示行（显示当前作用对象：选区摘要或当前段落）。
- **D3 作用域解析**：优先划词选区（_selectedTextCache），无选区回退聚焦段落（_focusController.activeParagraphId），再回退首段；触发后关闭键盘并打开伴读弹窗展示结果（复用 _triggerCompanion 与 ai.companion_ask 契约）。
- **D4 入口**：顶栏新增「AI 键盘 (Cmd+K)」按钮 + Cmd/Ctrl+K 快捷键；顶栏原 AI 伴读按钮行为不变（直接开伴读弹窗），既有测试不受影响。

---

## 2. 验收标准

1. 面板渲染四模板按钮 + 认知伴读入口 + 作用域提示行；
2. 点模板：键盘关闭、伴读弹窗打开并显示对应模板分析（e2e）；
3. 无划词时作用域自动回退段落（单测覆盖解析纯函数）；
4. Cmd/Ctrl+K 可切换键盘（Shortcuts 意图）；全量测试绿。

---

## 3. 执行步骤 (Checklist)

- [x] 1. 详设（本文件）
- [x] 2. 红灯：ai_keyboard_panel_test（面板渲染/回调/作用域解析）
- [x] 3. 绿灯：panel 组件 + main.dart 接线（状态/快捷键/作用域解析）
- [x] 4. 全量回归（47 passed）+ 提交

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
frontend/lib/features/ai_keyboard/presentation/ai_keyboard_panel.dart [新增]
frontend/lib/features/ai_keyboard/domain/ai_target_resolver.dart      [新增] 作用域解析纯函数
frontend/lib/main.dart                                                [修改] 状态/入口/快捷键
frontend/test/ai_keyboard_test.dart                                   [新增]
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`新增 5 用例（作用域解析 4 / 面板 1）；全量 47 passed`
- 契约比对：`复用 ai.companion_ask，无新 FFI 契约`
