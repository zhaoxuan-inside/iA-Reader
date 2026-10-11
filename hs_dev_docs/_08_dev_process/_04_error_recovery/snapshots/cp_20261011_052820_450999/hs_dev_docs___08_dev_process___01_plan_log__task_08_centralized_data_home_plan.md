# 任务计划账本：task_08_centralized_data_home

- **task_id**：`task_08_centralized_data_home`
- **标题**：运行期产物集中到 ~/.ai-reader（data/config/logs/books）+ 可配置位置 + 旧位置自动迁移
- **change_size**：`M`
- **work_mode**：`IMPLEMENT`
- **当前阶段**：`M 路径 - 详设完成，进入测驱动实现`
- **断点**：`S3` — Rust paths.rs / log.rs TDD
- **更新时间**：`2026-10-11T00:00:00Z`

---

## 背景与目标

db 散落（CWD/HOME/~/.local/share）、配置在 ~/.config/ai-reader、无文件日志。
目标布局与迁移规则见 ADR_005：`AI_READER_HOME` env 或默认 `~/.ai-reader`，
内部 config/data/logs/books 分区，配置文件键 data_dir/log_dir/books_dir 可重定位，
旧位置幂等迁移（只复制不删除），导入文档复制稳定副本入 books/。

## Seam 表

| Seam | 观察什么 | 抓住什么 | 抓不住什么 |
|------|----------|----------|------------|
| `paths::resolve_base` | base 路径 | env 优先级、默认拼接 | HOME 不存在的怪例 |
| `paths::migrate_file` | 复制发生/跳过 | 幂等（目标存在不覆盖） | 权限错误细节 |
| `paths::dirs_from_config` | 分区重定位 | data_dir/log_dir/books_dir 键生效 | 路径合法性深度校验 |
| `log::log` | 文件行格式 | 时间戳/级别/落盘 | 轮转策略 |
| `service.doc_parse`（books 副本） | file_path=副本路径 | sha256 命名、失败降级 | 源文件损坏 |
| FFI `config.get` | paths 数据 | 引擎侧路径解析（ctypes 冒烟） | UI 呈现 |

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S0 | 任务创建与 plan_log 建立 | done | task_manager + IN_PROGRESS |
| S1 | ADR_005 + 任务详情 seam 表 | done | `_00_project/_05_decision_record/ADR_005_centralized_data_home.md` |
| S2 | checkpoint 快照（改文件前） | pending | process_log checkpoint |
| S3 | Rust TDD：paths.rs（resolve_base/migrate/dirs_from_config）+ log.rs + db/config/ffi 接线 + doc_parse books 副本 + prints→logger | pending | sha2 新依赖 |
| S4 | Python 对齐：reader_engine.py base/config/db 迁移 + books 副本 | pending | 跑现有 Python 测试 |
| S5 | Flutter：设置页「存储位置」区块 + bridge mock + widget 测试 | pending | 只读展示 |
| S6 | 门禁：cargo test + python 测试 + flutter analyze/test + 构建 + verify_consistency | pending | 全绿为准出 |
| S7 | 重打包安装 + 迁移冒烟（旧 db/config 自动搬迁） | pending | 复用 chroot 安装通道 |
| S8 | change_log 归档 + 本地 Commit | pending | 默认本地 commit，不 push |

## 验收准则（DoD）

1. `cargo test` 全绿（paths/log/books 新增 seam 覆盖）；
2. Python 既有测试全绿；`flutter analyze` 0 error、`flutter test` 全绿；
3. `verify_consistency.py` 通过；
4. 安装态冒烟：HOME 的旧 db 与 ~/.config/ai-reader 旧配置自动出现在 ~/.ai-reader 对应位置；
   引擎日志落盘 `<base>/logs/ai_reader.log`；
5. 设置页展示解析后的存储位置；`AI_READER_HOME` 环境变量可整体重定向。
