# ADR 004: LLM 设置页的配置 I/O 归属与 FFI 契约

**状态**：ACCEPTED
**决策日期**：2026-10-11
**关联任务**：`task_07_llm_settings_ui`

---

## 1. 决策背景 (Context)

task_06 后真实 LLM 伴读依赖 `~/.config/ai-reader/llm_config.json`，但无应用内配置界面，
用户需手编 JSON。需要设置页，并决定配置文件读写的归属层与 FFI 契约。

## 2. 决策选项 (Options Considered)

1. **Option 1: 引擎层拥有配置 I/O（新增 config.* FFI action）**：路径、合并、校验逻辑
   与 `LlmConfig::load` 同处 `llm.rs`，单一真相源；Flutter 只渲染表单。
2. **Option 2: Dart 经 path_provider 直接读写配置文件**：UI 层自洽，但配置路径/合并语义
   在 Dart 与 Rust 双份漂移，且桌面端 path_provider 引入新插件依赖。
3. **Option 3: 仅提供文档引导用户手编**：零开发量，违背易用性诉求。

## 3. 决策结果 (Decision Outcome)

**选择 Option 1**，FFI 契约：

- `config.get` → `{ config: {provider, endpoint, api_key, model_name, temperature,
  max_output_tokens, system_prompt}, config_path: "<用户配置绝对路径>" }`
  （api_key 明文回传：本机本地优先架构，与 Python CLI 引擎既有语义一致）；
- `config.save`（payload `config` 为部分或全量字段）→ 键级 merge 到当前生效配置后校验
  （endpoint 必须 http(s):// 开头、temperature ∈ [0,2]、max_output_tokens ∈ [1,8192]），
  通过则写入用户配置文件（目录自动创建），返回 `{saved, config_path}`；
  校验失败返回 `code 50001` 与可读 message；
- `config.test`（payload 可带未保存的 `config` 先行验证）→ 单次真实调用（不重试），
  成功返回 `{ok, latency_ms}`，失败/无 key 返回错误 message。

UI 形态（iA Writer 极简）：书库顶栏齿轮 → 模态设置对话框（无独立路由）；
伴读抽屉检测到离线降级响应时展示直达配置入口。离线判定：响应前缀 `【离线模式】`。

## 4. 后续影响 (Consequences)

### 正向影响
- 配置读取/写入/校验单点在引擎，CLI（Python）与桌面端天然共享同一份用户配置；
- `config.test` 让用户在保存前即可验证 key，避免盲目保存；
- Flutter 侧零文件系统依赖，5 端可移植。

### 风险与应对
- api_key 明文落盘 → 本地优先产品的既有取舍（与 Python 引擎一致），文件权限为用户私有目录；
- 配置被并发写 → 单写者（设置对话框）+ 原子性由单文件整体覆写保证；引擎每次调用重读，
  无缓存失效问题。
