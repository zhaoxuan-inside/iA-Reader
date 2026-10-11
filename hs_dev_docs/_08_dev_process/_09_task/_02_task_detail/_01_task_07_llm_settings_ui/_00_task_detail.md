# 任务详细设计与执行记录：task_07_llm_settings_ui

- **任务名称**：LLM伴读设置页：config读写/连接测试FFI + iA极简设置对话框 + 离线提示入口
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T04:58:25Z`
- **最后更新**：`2026-10-11T05:12:57Z`

---

## 1. 任务背景与目标

task_06 落地真实 LLM 伴读后需手编 JSON 才能启用。本任务交付应用内配置页面：
书库顶栏齿轮 → iA 极简设置对话框（endpoint/api_key/model/temperature/max_tokens/system_prompt），
支持保存前连接测试；伴读抽屉检测离线降级时展示「立即配置」直达入口。

设计决策见 ADR_004：配置 I/O 归属引擎层（FFI `config.get/save/test`），Flutter 零文件系统依赖。

### Seam 表
| Seam | 观察什么 | 抓住什么 | 抓不住什么 |
|------|----------|----------|------------|
| `llm::save_user_config` | 写文件+回读字段 | 校验/目录自建/JSON 落盘 | 文件系统怪例 |
| `llm::test_llm_connection` | Ok(latency)/Err(msg) | 无 key 拒绝、单次不重试、错误透传 | 真实 endpoint 质量 |
| `llm::overlay_config` | merge 后字段 | 键级覆盖、缺省回落 | — |
| FFI `config.get/save/test` | 信封 code/data | 引擎侧契约（ctypes 冒烟） | UI 呈现 |
| Flutter `LlmSettingsDialog` | 表单回填/保存/测试反馈 | mock 通道行为、校验提示 | 真机键盘流 |

---

## 2. 验收标准
1. `cargo test` 20/20 绿（roundtrip/目录自建/校验拒绝/无 key 不调用/延迟/错误透传/overlay）；
2. `flutter analyze` 0 error、`flutter test` 8/8 绿（含设置对话框保存流与测试连接流）；
3. `verify_consistency.py` PASS；
4. 安装态：config 三通道 ctypes 冒烟通过，GUI 启动 + 引擎 FFI 回环正常。

---

## 3. 执行步骤 (Checklist)
- [x] 1. 设计文档（ADR_004 + plan_log + seam 表）
- [x] 2. DB 迁移：无 schema 变更（纯配置能力）
- [x] 3. 核心逻辑：llm.rs config 五函数 + ffi.rs 三 action + Flutter 设置对话框/入口/离线提示
- [x] 4. 单测：cargo 20 项 + flutter widget 2 项（新增）+ ctypes 安装态冒烟
- [x] 5. 门禁：cargo/flutter analyze/flutter test/verify_consistency 全绿；deb 重打包安装

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/src/llm.rs                    # +user_config_path/validate_config/save_user_config/overlay_config/test_llm_connection + 7 测试；LlmConfig 加 Serialize
backend/src/ffi.rs                    # +config.get / config.save / config.test 三 action
frontend/lib/features/settings/presentation/settings_dialog.dart  # 新增 LlmSettingsDialog
frontend/lib/features/library/presentation/library_screen.dart    # 顶栏齿轮入口
frontend/lib/features/companion/presentation/companion_drawer.dart # offlineMode 提示条 + onOpenSettings
frontend/lib/main.dart                # _companionOffline 检测与传参
frontend/lib/core/ffi/reader_engine_bridge.dart                   # config.* mock 通道（含修复错位大括号）
frontend/test/widget_test.dart        # +设置对话框 2 项 widget 测试
```

---

## 5. 验证与门禁记录
- `cargo test`：20/20 绿
- `flutter analyze`：0 error（存量风格 info 不计）
- `flutter test`：8/8 绿
- `flutter build linux --release`：成功
- ctypes 安装态冒烟：config.save/get 回读一致；无 key test 拒绝（code 50001 可读文案）
- 安装：docker chroot dpkg（清陈旧锁后成功）+ GUI 启动引擎回环正常
- `verify_consistency.py`：PASS
- 已知事项：api_key 明文落盘为本地优先产品既有取舍（ADR_004）
