# 任务详细设计与执行记录：task_06_real_llm_companion

- **任务名称**：接入真实LLM认知伴读到Rust桌面主链路（重试/降级/持久化/isolate化）
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T00:35:33Z`
- **最后更新**：`2026-10-11T01:04:24Z`

---

## 1. 任务背景与目标

PRD F-04 要求深度认知伴读（4 模板、指数退避重试、离线启发式降级、TTFT 度量）。
现状：Rust `service.ai_companion_stream` 返回 `format!` 罐头文本（假 AI），桌面端 FFI
主链路 `ai.companion_ask` 只能返回假回复；真实 LLM 调用仅在 Python CLI 侧。
本任务将真实 LLM 调用接入 Rust 桌面主链路，FFI 信封契约保持不变。

设计决策：`hs_dev_docs/_00_project/_05_decision_record/ADR_003_llm_companion_integration.md`
（ureq+rustls 同步客户端；配置路径与 Python 引擎同构；非流式先行，流式留 task_07）。

### Seam 表（测试面）

| Seam | 观察什么 | 抓住什么 | 抓不住什么 |
|------|----------|----------|------------|
| `llm::LlmConfig::load_from` | 合并后的字段值 | 用户>默认>内建优先级、缺省值 | 文件系统权限怪例 |
| `llm::chat_with_retry` | Ok(内容)/Err + 退避 sleep 序列 | 重试编排与耗尽语义 | ureq 网络协议细节 |
| `llm::build_companion_messages` | messages 角色/内容 | 4 模板 prompt 组装、追问拼接 | 模型实际回复质量 |
| `service.ai_companion_stream_with` | response + 入库会话 + mock 调用次数 | 无 key→离线降级、重试耗尽→降级、成功→真实回复入库 | 真实 LLM 输出质量 |
| Flutter `ReaderEngineBridge.invoke` | Future<InvokeEnvelope> 且 UI 不阻塞 | isolate 隔离、FFI 异常回退 mock | FFI 内存细节 |

---

## 2. 验收标准
1. `cargo test` 全绿：覆盖无 key→离线降级（不发起调用）、重试耗尽→降级、成功→真实回复+会话入库、4 模板 prompt 组装、配置合并优先级、指数退避序列；
2. `flutter analyze` 0 error、`flutter test` 全绿；
3. `verify_consistency.py` 通过；
4. 未配置 api_key 时行为与现状一致（离线卡片，零网络调用）。

---

## 3. 执行步骤 (Checklist)
- [x] 1. 完善设计文档与接口定义（ADR_003 + 方法设计 §2.6 + llm.rs seam）
- [x] 2. DB 迁移：无 schema 变更（description 列建表已有，仅修复 INSERT 遗漏）
- [x] 3. 核心六元组业务逻辑（ai_companion_stream 真实 LLM + 降级编排）
- [x] 4. 全覆盖单测（Rust 13 项 seam 测试）与 ctypes 集成冒烟
- [x] 5. 本地质量门禁与提交前自检（cargo test / flutter test / verify_consistency 全绿）

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/Cargo.toml                    # 新增 ureq 2.10（json/tls/gzip，rustls 免 openssl）
backend/src/llm.rs                    # 新增：LlmConfig/LlmClient trait/chat_with_retry/build_companion_messages/UreqLlmClient + 9 项测试
backend/src/lib.rs                    # 注册 llm 模块
backend/src/service.rs                # ai_companion_stream 真实 LLM 编排 + with_llm_client 注入 + 模板化离线降级 + 4 项测试
backend/src/storage.rs                # 修复 save_ai_conversation 未写 description 列；清理无用 import
frontend/lib/core/ffi/reader_engine_bridge.dart  # 原生 FFI 移入 Isolate.run；FLUTTER_TEST 跳过库自动发现
hs_dev_docs/_00_project/_05_decision_record/ADR_003_llm_companion_integration.md  # 新增
hs_dev_docs/_06_method_design/_01_reader_core/_01_reader_six_tuple_method_design.md  # §2.6 更新
hs_dev_docs/_08_dev_process/_01_plan_log/task_06_real_llm_companion_plan.md  # 新增
```

---

## 5. 验证与门禁记录
- `cargo test`：13/13 绿（配置合并 2 / 重试编排 3 / 模板组装 2 / 传输层 2 / service 降级编排 4）
- `flutter analyze`：0 error（15 条存量风格 info 与 1 条存量 warning 非本次引入）
- `flutter test`：6/6 绿（修复：FLUTTER_TEST 环境跳过原生库自动发现，测试确定性走 mock 通道）
- `flutter build linux --release`：构建成功
- ctypes 集成冒烟（真 .so + /tmp 隔离 db）：`ai.companion_ask` 无 key → 离线卡片、信封 code=0、FK 失败按设计记日志不崩溃
- `verify_consistency.py`：PASS
- 已知限制（留 task_07）：Rust 侧单 Mutex 串行化，LLM 调用期间阻塞其他 FFI action；流式输出未实现（ADR 003 非流式先行）
