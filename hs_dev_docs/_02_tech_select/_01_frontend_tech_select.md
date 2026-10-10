# 前端与多端客户端技术选型报告 (Flutter Desktop & Mobile)

- **模块名称**：前端与客户端呈现层 (Frontend / Client Layer)
- **选型结论**：采用 **Flutter** 跨平台应用框架 (支持 Windows, macOS, Linux, iOS, Android 5端)
- **文档版本**：v1.0.0
- **日期**：2026-10-10
- **状态**：APPROVED

---

## 1. 选型背景与业务诉求

在《AI Reader 产品需求规格说明书 (v4.0.0)》中，AI Reader 已由纯 Headless 计算引擎升级为具备极简沉浸式阅读体验的多端智能阅读器。
客户端需要满足以下核心诉求：
1. **多端一致性 (5端覆盖)**：一套代码库运行于 Windows、macOS、Linux 桌面端与 iOS、Android 移动端；
2. **像素级排版与 iA Writer 极简美学**：需要极高自由度的 Canvas / TextPainter 绘制能力，支持严格的行高、字符间距、段落级失焦弱化（Focus Mode）与悬浮胶囊；
3. **零额外 Web 运行时开销**：避免 Electron / Webview 等高内存占用框架，启动迅速、内存可控（< 80MB）；
4. **低延迟原生 FFI 调用**：能够通过 `dart:ffi` 直接调用核心 Rust / C-ABI 动态库（`ai_reader_invoke`），实现微秒级本地进程内交互。

---

## 2. 候选方案对比分析

| 评估维度 | 方案 A: Flutter (本案选定) | 方案 B: Tauri + React/Vue | 方案 C: Qt / PyQt6 |
|---|---|---|---|
| **多端覆盖度** | **全平台 5 端（Desktop + Mobile 原生支持）** | 桌面端优秀；移动端 (Tauri v2) 生态较新 | 桌面端支持好；移动端生态繁琐、打包笨重 |
| **排版与渲染性能** | 自研 Skia / Impeller 引擎，像素级可控，60~120fps | 依赖系统 Webview，不同平台字体渲染存在细微差异 | 原生 QPainter / QML，但跨端适配较重 |
| **内存与启动** | 启动 < 300ms，内存 50~80MB | 启动 < 200ms，内存 40~70MB | 启动 < 400ms，内存 60~100MB |
| **跨语言 FFI** | 原生 `dart:ffi`，零跨进程 IPC 损耗，直接共享内存 | Rust 作为宿主通过 IPC / Webview 通信，需要序列化 | 原生 C++ / Python 绑定 |
| **iA 风格定制难度** | 极佳（可精确控制段落透明度、行间距与无边框药丸） | 良好（CSS 易编写，但多端 Webview 字体度量不一） | 良好但样式 QSS 维护繁琐 |

---

## 3. 选型决策与落地规范

1. **采用 Flutter 3.x 稳定通道**：
   - 使用 `dart:ffi` 绑定底层核心引擎六元组接口 `ai_reader_invoke`；
   - 采用标准状态管理（Riverpod 或 BLoC）解耦 UI 表现与伴读流式状态；
2. **多端自适应响应式布局**：
   - 桌面端（断点宽 ≥ 1024px）：采用左目录抽屉 + 中央黄金版心 (700px) + 右侧认知伴读抽屉三栏架构；
   - 移动端（断点宽 < 1024px）：采用单栏全屏阅读流 + 底部可拖拽 Bottom Sheet 伴读；
3. **严格遵守 DESIGN.md**：
   - 默认集成高质感衬线与等宽中英文字体，行高 `1.65`，严格执行段落失焦淡化动画。
