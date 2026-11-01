# AI Reader

本地优先的沉浸式 AI 认知阅读器：Flutter（Linux/GTK）桌面客户端 + Rust 核心引擎（C-ABI 单入口 `ai_reader_invoke`）。

## 核心能力

- **书库与导入**（FEAT-001）：文件选择器导入 Markdown/TXT，SHA-256 去重幂等定位，空/超大文件拦截
- **沉浸阅读**（FEAT-002/003）：H1-H6 层级章节树、行内 Markdown 语义渲染、700px 版心、聚焦模式、3s 静止顶栏隐退、续读进度持久化
- **AI 认知伴读**（FEAT-004/005/006）：划词胶囊、流式卡片（TTFT 展示）、原位追问（多轮线程上下文）、OpenAI 兼容端点、离线启发降级、未配置引导
- **多维标注**（FEAT-007）：7 种标注样式 × 6 色调色板、人工批注、AI 沉淀边注（幂等归档）、锚点回跳
- **知识可视化**（FEAT-008/009）：三层知识导图（根/章节/核心词）、TF-IDF×TextRank 词云、点击定位原文
- **AI 快捷操作**（FEAT-010）：独立 AI 键盘、作用域解析、数字键直触
- **多端与治理**（FEAT-011）：Linux deb 交付（Windows/Android 脚手架就绪）、数据集中 `~/.ai-reader`、密钥 AES-GCM 加密存储、SQLite WAL + 事务 + user_version 迁移

## 引擎统一契约

GUI 与无头 CLI 共用同一 Rust 引擎（`libreader_core.so` 的 `dispatch_invoke`），同一 action 在两种宿主下结构与行为完全一致：

```bash
ai_reader_cli parse <file>                 # 解析入库
ai_reader_cli invoke --action book.list --pretty
ai_reader_cli keywords <book_id>           # 词云
ai_reader_cli mindmap <book_id>            # 导图
```

## 构建与门禁

```bash
make check      # lint（clippy -D warnings + flutter analyze）+ 全量测试
make test       # cargo test + flutter test + python 契约/端到端/CLI/规格
make bench      # 性能 SLA（10万字解析<1.5s / NLP<200ms / 离线卡片<10ms）
make build-deb  # Linux deb + 产物清单/校验和同步
```

## 目录

```
backend/    Rust 引擎（src/bin/ai_reader_cli.rs 为无头 CLI）
frontend/   Flutter 客户端（linux/windows/android 平台脚手架）
packaging/  deb/desktop/icon/打包配置
scripts/    构建与产物清单脚本
test/       分层测试（e2e/method/contract/performance，ctypes 直调真 .so）
```

数据与日志集中于 `~/.ai-reader`（可用 `AI_READER_HOME` 重定位）。
