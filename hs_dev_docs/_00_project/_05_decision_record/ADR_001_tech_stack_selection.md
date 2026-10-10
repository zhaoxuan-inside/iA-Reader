# ADR 001: 跨平台基础技术栈选型决策 (Flutter + Rust + SQLite)

**状态**：ACCEPTED  
**决策日期**：2026-10-10  
**决策者**：项目架构委员会  

---

## 1. 决策背景 (Context)

AI Reader 旨在实现全格式沉浸阅读（PDF/EPUB/MD/TXT）、iA Writer 边注、深度认知伴读模板、本地离线三级 NLP 概念图谱与全端自适应响应。项目必须跨 5 大终端（Linux、Windows、macOS、Android、iOS）提供极致一致的排版美感、零 GC 停顿的高性能离线分词计算以及本地高可靠存储。

## 2. 决策选项 (Options Considered)

1. **Option 1: Flutter (UI) + Rust (Core Engine) + SQLite (Storage)**：UI 统一 Canvas 自绘，核心计算由 Rust 原生编译与 FFI 嵌入，本地 SQLite WAL 模式存储。
2. **Option 2: Electron + React/TS + Python 后台**：Web 技术栈开发速度快，但客户端资源消耗大（>250MB），移动端无法平滑复用。
3. **Option 3: 纯 Flutter/Dart 全栈**：单语言开发，但 Dart 解析几十兆复杂 PDF 与 10 万字分词共现矩阵时性能不足且容易卡顿。

## 3. 决策结果 (Decision Outcome)

**选择 Option 1**：
- **表现层**：采用 Flutter 3.x，实现全平台统一像素级排版与 60fps 交互；
- **核心计算层**：采用 Rust (2021 Edition)，负责高吞吐文档解构、离线 NLP 分词（`jieba-rs` / `textrank`）、图谱与思维导图生成；
- **存储层**：采用 SQLite 3 (`rusqlite` + WAL 模式)，保证无网络环境下 100% 完整功能可用与原子事务。

## 4. 后续影响 (Consequences)

### 正向影响 (Positive)：
- 达成 10 万字书籍离线分析 < 1.0s 的硬核性能指标；
- 避免平台间排版差异与渲染错位；
- 架构分层清晰，便于六元组标准化运行时落位。

### 风险与应对 (Mitigation)：
- 跨语言 FFI 边界调试相对复杂 -> 采用统一 JSON Envelope 信封契约，并在 Dart 与 Rust 两端均提供独立 Mock 隔离通道。
