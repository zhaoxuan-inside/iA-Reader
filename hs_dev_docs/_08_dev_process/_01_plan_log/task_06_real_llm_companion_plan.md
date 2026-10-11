# 任务计划账本：task_06_real_llm_companion

- **task_id**：`task_06_real_llm_companion`
- **标题**：接入真实 LLM 认知伴读到 Rust 桌面主链路（重试 / 降级 / 持久化 / isolate 化）
- **change_size**：`M`
- **work_mode**：`IMPLEMENT`
- **当前阶段**：`6 - 门禁全绿，COMPLETED`
- **断点**：`S7` — S7
- **更新时间**：`2026-10-11T01:04:24Z`

---

## 背景与目标

PRD F-04 要求深度认知伴读（4 模板、指数退避重试、离线启发式降级、TTFT 度量）。
现状：Rust `service.ai_companion_stream` 返回 `format!` 罐头文本（假 AI），Flutter 桌面端
走 FFI 主链路只能看到假回复；真实 LLM 调用仅存在于 Python CLI 侧（`reader_engine.py`）。
本任务将真实 LLM 调用接入 Rust 桌面主链路，保持 FFI 信封契约不变。

## 设计决策（详见 ADR_003）

1. HTTP 客户端选型 `ureq` + `rustls`（同步、免 openssl，匹配现有全同步架构，打包友好）；
2. 配置读取与 Python 引擎同路径：`~/.config/ai-reader/llm_config.json` → `config/default_llm_config.json` 回退；
   `api_key` 为空 → 直接离线启发式降级（不发起 HTTP、零计费风险）；
3. 本迭代为非流式一次调用（PRD 流式体验留待 task_07 FFI 轮询迭代），TTFT 记入 metrics 与会话；
4. FFI `ai.companion_ask` 契约（payload/response 字段）不变；
5. Flutter bridge 原生调用移入 `Isolate.run`，避免秒级 LLM 阻塞 UI 线程（顺带惠及 doc.parse）。

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S0 | 任务创建与 plan_log 建立 | done | task_manager create + IN_PROGRESS |
| S1 | 触达面详设 + ADR_003（LLM 集成选型与降级编排） | done | `_00_project/_05_decision_record/ADR_003_llm_companion_integration.md` |
| S2 | checkpoint 快照（改文件前） | doing | process_log checkpoint |
| S3 | Rust llm 模块 TDD：LlmConfig 读取 / 重试 / 降级（trait seam + mock） | done | `backend/src/llm.rs` + `cargo test` 红绿 |
| S4 | service.ai_companion_stream 接真实调用 + 会话持久化 + 模板 prompt 组装 | done | 六元组主方法升级 |
| S5 | Flutter bridge isolate 化（Isolate.run 包裹原生 invoke） | done | 消除 UI 阻塞 |
| S6 | 门禁：cargo test + flutter analyze/test + verify_consistency | doing | 全绿为准出 |
| S7 | change_log 归档 + 本地 Commit | doing | 默认本地 commit，不 push |

## 验收准则（DoD）

1. `cargo test` 全绿：覆盖 api_key 缺失→降级、mock LLM 成功→真实回复+入库、连续失败→3 次指数退避后降级、4 模板 prompt 组装；
2. `flutter analyze` 0 error、`flutter test` 全绿；
3. `verify_consistency.py` 通过；
4. 未配置 api_key 时桌面端划词伴读行为与现状一致（离线启发卡片），配置后返回真实 LLM 内容。
