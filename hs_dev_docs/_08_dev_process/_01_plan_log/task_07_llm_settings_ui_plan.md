# 任务计划账本：task_07_llm_settings_ui

- **task_id**：`task_07_llm_settings_ui`
- **标题**：LLM 伴读设置页（config 读写/连接测试 FFI + iA 极简设置对话框 + 离线提示入口）
- **change_size**：`M`
- **work_mode**：`IMPLEMENT`
- **当前阶段**：`6 - 门禁全绿，COMPLETED`
- **断点**：`S7` — S7
- **更新时间**：`2026-10-11T05:12:25Z`

---

## 背景与目标

task_06 落地真实 LLM 伴读后，用户只能手编 `~/.config/ai-reader/llm_config.json` 才能启用。
本任务交付应用内配置页面：查看/编辑 endpoint、api_key、模型、temperature、max_tokens、
system_prompt；支持连接测试；伴读离线降级时在抽屉内提供直达入口。

## 设计决策（详见 ADR_004）

1. 配置 I/O 归属引擎层：新增 FFI `config.get` / `config.save` / `config.test`，
   Flutter 不直接触碰文件系统，路径与读取逻辑单一真相源在 Rust `llm.rs`；
2. `config.save` 写用户级 `~/.config/ai-reader/llm_config.json`（merge 语义，缺省字段回落当前生效配置）；
3. `config.test` 单次真实调用（不重试），payload 可携带未保存的表单值先行验证；
4. UI 走 iA 极简：书库顶栏齿轮 IconButton → 设置对话框；伴读抽屉离线降级时展示
   「配置 LLM 启用真实伴读」直达按钮。

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S0 | 任务创建与 plan_log 建立 | done | task_manager + IN_PROGRESS |
| S1 | ADR_004 + 任务详情 seam 表 | done | `_00_project/_05_decision_record/ADR_004_llm_settings_ui.md` |
| S2 | checkpoint 快照（改文件前） | doing | process_log checkpoint |
| S3 | Rust TDD：user_config_path / save_user_config / validate / test_llm_connection / overlay_config + ffi 三 action | done | `llm.rs` + `ffi.rs`，temp 路径测试零污染 |
| S4 | Flutter：SettingsDialog + 书库入口 + 抽屉离线提示 + bridge mock + widget 测试 | doing | `features/settings/` |
| S5 | 门禁：cargo test + flutter analyze/test + flutter build linux | done | 20/20 + 8/8 + 0 error + 构建成功 |
| S6 | 重新打包 deb + docker chroot 安装 + 启动验证 | done | 清陈旧 dpkg 锁后安装；安装态 config 冒烟 + GUI 启动通过 |
| S7 | change_log 归档 + 本地 Commit | doing | 默认本地 commit，不 push |

## 验收准则（DoD）

1. `cargo test` 全绿：配置保存/回读 roundtrip、目录自建、非法 endpoint/temperature 校验、
   连接测试（无 key 不发调用 / 成功回报延迟 / 失败透传错误）、overlay 合并；
2. `flutter analyze` 0 error、`flutter test` 全绿（含设置对话框渲染与保存流）；
3. `verify_consistency.py` 通过；
4. 安装态：书库齿轮 → 对话框可改可存 → `~/.config/ai-reader/llm_config.json` 生效（引擎下次调用即用新值）；
5. 连接测试按钮在 key 无效时给出可读错误，有效时回报延迟。
