# 任务详细设计与执行记录：task_17_concurrent_stream

- **任务名称**：清零遗留②——FFI 并发治理（LLM 不占全局锁）+ 流式伴读 companion_start/poll + 前端渐进渲染
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：agent
- **开始时间**：`2026-10-11T19:35:00Z`

---

## 1. 任务背景与目标

ADR_003 挂账两项架构遗留：①Rust 侧单全局 `Mutex<ReaderService>` 使 LLM 秒级调用期间其他 FFI action 全部串行化阻塞；②伴读无流式输出（TTFT 无法 <800ms，长回复需整体等待）。本任务一并清零。

### 设计决策

- **D1 SSE 流式传输层**：`LlmClient` 新增 `chat_stream(config, messages, on_delta)` 带默认实现（降级为 chat() 整段回调，既有 Mock 零改动）；`UreqLlmClient` 覆写为 OpenAI 兼容 SSE（`"stream": true`，逐行解析 `data:` 帧 `choices[0].delta.content`，`[DONE]` 终止）；`parse_sse_delta_line` 提为可测纯函数。重试包装 `chat_with_retry_stream`：重试后以返回全文为权威（中途已发 delta 可能重复，终态覆盖，注释说明取舍）。
- **D2 流式注册表（免锁核心）**：`static COMPANION_STREAMS: Mutex<HashMap<id, Arc<Mutex<CompanionStreamState{partial,done,offline}>>>>`；`companion_start(client, storage, config, ...) -> request_id` 自由函数——锁内只做 storage.clone() 取句柄（SqliteStorage=Arc 内核可 Clone），LLM 调用与持久化全部在派生线程，全程不占 SERVICE Mutex；`companion_poll(id)` 读注册表。
- **D3 companion_ask 契约兼容**：改为 start + 30ms 轮询 join（180s 上限），返回信封不变——既有调用方/测试零迁移；dispatch 对 companion 三 action 走免锁前置分支。
- **D4 前端渐进渲染**：`_triggerCompanion` 改为 `companion_start` → 260ms 轮询 → `_activeAnalysisText` 逐步刷新 → done 落终态（离线标记沿用前缀判断）；mock 端 start 即 done（确定性，测试零等待）。

---

## 2. 验收标准

1. cargo：离线路径 start→poll 往返（done+offline+【离线模式】前缀）；Mock 客户端非流式默认实现路径 done；SSE 行解析纯函数用例；
2. cargo 全量绿（既有 chat_with_retry / companion 测试不受影响）；
3. dart：mock companion_start/poll 往返；e2e 伴读流经 start/poll 后照常出卡；
4. 全量 flutter test 绿 + release 构建通过。

---

## 3. 执行步骤 (Checklist)

- [x] 1. llm.rs：chat_stream + chat_with_retry_stream + parse_sse_delta_line + cargo 测试
- [x] 2. service.rs：companion_offline_text 自由化 + 流注册表 + companion_start/poll
- [x] 3. ffi.rs：companion 三 action 免锁分支 + companion_ask join 兼容
- [x] 4. mock companion_start/poll + main 渐进渲染 + dart 测试
- [x] 5. 全量回归（cargo 31 + flutter 57）+ 提交

### 排障记录
- `into_reader()` 返回 `Box<dyn Read>` 无 lines —— 包 BufReader + BufRead；
- companion_poll 的 `?` 与锁守卫生命周期三次冲突 —— 注册表取值块内 clone 后再锁快照；
- InvokeEnvelope.data 非空，mock 错误信封用 `{}` + code 50001。

---

## 4. 涉及文件修改清单 (Diff Tracking)

```text
backend/src/llm.rs          [修改] 流式 trait + SSE 解析
backend/src/service.rs      [修改] 注册表 + start/poll 自由函数
backend/src/ffi.rs          [修改] companion 免锁分支
frontend/lib/core/ffi/reader_engine_bridge.dart [修改] mock start/poll + reset 清流
frontend/lib/main.dart      [修改] _triggerCompanion 渐进渲染
backend tests / frontend tests [新增]
```

---

## 5. 验证与门禁记录

- 单测覆盖率：`cargo +4（SSE 解析/离线流往返/mock 流路径/未知 id）；flutter +1（mock start/poll 往返）；cargo 31 + flutter 57 全绿`
