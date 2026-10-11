# ADR 003: 认知伴读真实 LLM 集成选型与降级编排 (ureq + 配置文件 + 非流式先行)

**状态**：ACCEPTED
**决策日期**：2026-10-11
**关联任务**：`task_06_real_llm_companion`

---

## 1. 决策背景 (Context)

PRD F-04 要求深度认知伴读：4 大认知模板、指数退避重试、离线启发式降级、TTFT < 800ms 度量。
当前 Rust 引擎 `service.ai_companion_stream` 为硬编码罐头文本（假 AI），FFI 主链路
`ai.companion_ask` 无法返回真实智能内容；真实 LLM 调用仅存在于 Python CLI 侧
（`backend/reader_engine.py`，deepseek HTTP）。桌面端（deb 安装态）只携带 Rust
`libreader_core.so`，因此真实伴读能力必须内建于 Rust 引擎。

## 2. 决策选项 (Options Considered)

1. **Option 1: Rust 端同步 HTTP 客户端（ureq + rustls）**：无 tokio 运行时，依赖树小，
   与现有全同步 FFI 架构（`ai_reader_invoke` 阻塞式信封）完全匹配；rustls 免去 openssl
   系统依赖，打包（deb/rpm/arch）友好。
2. **Option 2: Rust 端 reqwest + tokio 异步运行时**：生态最强，但为一个同步信封 API 引入
   整套 async runtime，二进制体积与编译时间显著上升，且需要 bridge 线程模型改造。
3. **Option 3: Flutter Dart 层直连 LLM API**：绕开引擎层，违反"统一六元组 FFI 桥接"
   架构原则（ADR 001），配置/重试/持久化逻辑在 Dart 与 Rust 双份漂移。

## 3. 决策结果 (Decision Outcome)

**选择 Option 1**，并约定：

- **新模块** `backend/src/llm.rs`：
  - `LlmConfig`：读取 `~/.config/ai-reader/llm_config.json`，缺失回退 `<workspace>/config/default_llm_config.json`，字段与 Python 引擎同构（provider/endpoint/api_key/model_name/temperature/max_output_tokens/system_prompt）；
  - `LlmClient` trait（seam）：`chat(messages) -> Result<String, LlmError>`；生产实现 `UreqLlmClient`（OpenAI 兼容 `POST {endpoint}/chat/completions`），测试用 `MockLlmClient`；
  - 指数退避重试：最多 3 次，基础 300ms（测试可注入时钟/闭包）；
- **降级编排**（service 层六元组）：
  - `api_key` 为空 → 直接走离线启发式卡片（不发 HTTP，零计费风险）；
  - 调用失败重试耗尽 → 离线启发式卡片；两者均在会话记录中标记 `offline_fallback=true`；
- **契约不变**：`ai.companion_ask` 的 payload/response 字段保持不变（response 从罐头文本变为真实内容）；
- **非流式先行**：本迭代一次拿到完整回复；PRD 的流式体验（TTFT<800ms）留待下一迭代以
  FFI 轮询模式（companion.start / companion.poll）实现；TTFT/时延仍记入 metrics 与 SQLite 会话；
- **Flutter isolate 化**：`ReaderEngineBridge.invoke` 将原生 FFI 调用移入 `Isolate.run`，
  秒级 LLM 调用不再冻结 UI 线程（同时惠及 doc.parse 等重计算 action）。

## 4. 后续影响 (Consequences)

### 正向影响
- 桌面端划词伴读产出真实 LLM 内容，F-04 主路径闭环；
- trait seam 使重试/降级/持久化逻辑可脱离网络测试（`cargo test` 全离线）；
- 配置体系与 Python CLI 完全同构，两端共享同一份用户配置。

### 风险与应对
- 同步阻塞调用占用调用线程 → Flutter 侧 isolate 隔离 + Rust 侧不变；
- 无 api_key 时用户误以为功能损坏 → 降级卡片文案明确提示离线模式与配置路径；
- rustls 证书链在极简容器环境可能缺失 CA → 失败落入降级卡片，不崩溃（PRD §4.1）。
