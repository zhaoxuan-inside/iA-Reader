# 任务详细设计与执行记录：task_08_centralized_data_home

- **任务名称**：运行期产物集中到 ~/.ai-reader（data/config/logs/books）+ 可配置位置 + 旧位置自动迁移
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T05:27:31Z`
- **最后更新**：`2026-10-11T05:47:01Z`

---

## 1. 任务背景与目标

运行期产物此前散落四处（CWD/HOME 的 db、~/.local/share/ai-reader、~/.config/ai-reader、无文件日志）。
本任务按 ADR_005 集中到 `~/.ai-reader/`（base = env AI_READER_HOME > 默认），内部分区
config/ data/ logs/ books/；配置文件键 data_dir/log_dir/books_dir 可重定位；旧位置幂等迁移
（只复制不删除）；导入文档复制 SHA-256 稳定副本；引擎日志落盘。

### Seam 表
| Seam | 观察什么 | 抓住什么 | 抓不住什么 |
|------|----------|----------|------------|
| `paths::resolve_base` | base 路径 | env 优先级、默认拼接 | HOME 怪例 |
| `paths::migrate_file` | 复制发生/跳过 | 幂等（目标存在不覆盖） | 权限错误细节 |
| `paths::dirs_from_config` | 分区重定位 | data/log/books_dir 键生效 | 路径深度校验 |
| `log::log` | 文件行格式 | 时间戳/级别/落盘 | 轮转策略 |
| `service.doc_parse` books 副本 | file_path=副本 | sha256 命名、失败降级 | 源损坏 |
| FFI config.get paths | 路径解析结果 | 引擎侧契约（安装态冒烟） | UI 呈现 |

---

## 2. 验收标准
1. `cargo test` 26/26 绿（paths 5 + log 1 新增）；Python 既有测试 8/8 OK；
   `flutter analyze` 0 error、`flutter test` 8/8 绿；
2. `verify_consistency.py` PASS；
3. 安装态冒烟：HOME 旧 db 自动迁移至 ~/.ai-reader/data/ai_reader.db（日志留痕）；
   日志落盘 logs/ai_reader.log；AI_READER_HOME 整体重定向生效。

---

## 3. 执行步骤 (Checklist)
- [x] 1. 设计文档（ADR_005 + plan_log + seam 表）
- [x] 2. DB 迁移脚本：无 schema 变更（仅 db 文件位置迁移）
- [x] 3. 核心逻辑：paths.rs/log.rs + ffi/llm/service 接线 + Python 引擎对齐 + Flutter 存储位置区块
- [x] 4. 单测：cargo 26 项、python 8 项、flutter 8 项（含存储位置断言）+ 安装态冒烟
- [x] 5. 门禁全绿；deb 重打包安装 + 迁移/env 重定向冒烟

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/src/paths.rs                # 新增：base 解析/幂等迁移/重定位键/运行时单例/books 副本 + 5 测试
backend/src/log.rs                  # 新增：文件日志（stdout 镜像 + 宏）+ 1 测试
backend/src/lib.rs                  # 注册 paths/log 模块
backend/src/ffi.rs                  # get_service 用 runtime db 路径；config.get 返回 paths
backend/src/llm.rs                  # user_config_path 切集中存储
backend/src/service.rs              # 27 处打印切 logger；doc_parse books 副本
backend/Cargo.toml                  # +sha2 0.10
backend/reader_engine.py            # base/config/db 迁移对齐 + books 副本 + welcome_guide 归位
frontend/lib/features/settings/presentation/settings_dialog.dart  # 存储位置区块 + 结构重构
frontend/lib/core/ffi/reader_engine_bridge.dart                   # config.get mock 带 paths
frontend/test/widget_test.dart      # +存储位置区块断言
```

---

## 5. 验证与门禁记录
- `cargo test`：26/26 绿
- Python `test_reader_core_engine.py`：8/8 OK
- `flutter analyze`：0 error；`flutter test`：8/8 绿
- `flutter build linux --release` + `cargo build --release`：成功
- `verify_consistency.py`：PASS
- 安装态冒烟：旧 db 迁移（日志留痕）、logs 落盘、8 张表完整、AI_READER_HOME 重定向 PASS
- 已知事项：旧位置文件按设计不删除（用户可自行清理 ~/ai_reader_data.db、
  ~/.local/share/ai-reader/、~/.config/ai-reader/）；重定位 UI 编排留后续迭代
