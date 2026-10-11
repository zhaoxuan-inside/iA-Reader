# ADR 005: 运行期产物集中存储于 ~/.ai-reader（可配置 + 自动迁移）

**状态**：ACCEPTED
**决策日期**：2026-10-11
**关联任务**：`task_08_centralized_data_home`

---

## 1. 决策背景 (Context)

当前运行期产物散落四处：Rust 桌面端 db 落在进程 CWD（deb 启动 = HOME，开发启动 = 仓库根）；
Python CLI db 在 `~/.local/share/ai-reader/`；两端 LLM 配置在 `~/.config/ai-reader/`；
仓库里还有空的 `logs/` 目录。用户要求：全部集中到 `~/.ai-reader/`，不散乱，且位置支持用户配置。

## 2. 决策选项 (Options Considered)

1. **Option 1: 统一 base 目录 `~/.ai-reader/`，内部 data/config/logs/books 分区**：
   一处可备份、可整目录搬走；XDG 多目录方案（~/.config + ~/.local/share）仍显散乱。
2. **Option 2: 严格 XDG 分目录**：符合 Linux 惯例，但跨 5 端（Windows/macOS/移动端）无
   对应直觉，且用户明确要求单根目录。
3. **Option 3: 保持 CWD 相对路径**：现状即问题本身。

## 3. 决策结果 (Decision Outcome)

**选择 Option 1**。目录布局与解析规则（Rust `paths.rs` 为单一真相源，Python 引擎镜像同规则）：

```
base = 环境变量 AI_READER_HOME（非空时） > $HOME/.ai-reader

<base>/
├── config/llm_config.json   # 用户 LLM 配置（引擎/CLI/设置页共享）
├── data/ai_reader.db        # SQLite（wal/shm 同目录）
├── logs/ai_reader.log       # 引擎文件日志（新增，stdout 同步镜像保留）
└── books/                   # 导入文档稳定副本（SHA-256 命名，库自包含）

config/llm_config.json 可选键（用户配置覆盖，进程启动时应用）：
  data_dir / log_dir / books_dir   # 绝对路径，分别重定位对应分区
```

- **迁移（幂等，引擎初始化时执行，只复制不删除）**：
  - 旧 db：`$HOME/ai_reader_data.db`、`./ai_reader_data.db`（CWD）、
    `~/.local/share/ai-reader/ai_reader_data.db` → 目标 `<data>/ai_reader.db` 缺失时按序复制首个命中者；
  - 旧配置：`~/.config/ai-reader/llm_config.json` → `<base>/config/llm_config.json` 缺失时复制；
  - 迁移动作记入文件日志。
- **日志**：新增 `log.rs`（全局追加写，时间戳行）；service/llm/ffi 的 println/eprintln
  全部改走 logger（文件 + stdout 镜像，CLI 可观察性不变）。
- **导入书籍副本**：`doc.parse` 成功后复制源文件至 `<books>/<sha256>.<ext>`，db `file_path`
  指向稳定副本（源文件移动/删除不再破坏书库）；复制失败降级为原路径（不阻断导入）。
- **设置页**：新增「存储位置」区块展示解析后的实际路径，并注明可用 `AI_READER_HOME`
  环境变量或配置文件键自定义（重定位语义：进程启动时应用，改后重启生效）。

## 4. 后续影响 (Consequences)

### 正向影响
- 一处备份/搬移整个用户数据；卸载重装不丢数据；多入口（GUI/CLI）共享同一书库与配置。
- db 不再随 CWD 漂移，仓库根/HOME 的散落文件成为历史。

### 风险与应对
- 迁移期间双份占用磁盘 → 只复制不删除，由用户自行清理旧文件（文档注明路径）；
- data_dir 指向不可写路径 → 初始化失败记日志并回退默认路径（不 crash）；
- 设置页本轮仅展示（重定位 UI 编排留后续迭代），配置文件/环境变量已满足「支持用户配置」。
