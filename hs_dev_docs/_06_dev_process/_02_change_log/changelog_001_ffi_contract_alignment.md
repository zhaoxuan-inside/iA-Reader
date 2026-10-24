# 变更记录：CFX-001 Linux 桌面端真链路契约对齐与解析诚实化

- **日期**：2026-10-24
- **intent / change_size / work_mode**：`FIX` / `M` / `IMPLEMENT`
- **范围裁定**：开发者指示"优先开发 Linux 桌面端，写代码考虑兼容性"；本切片为探索报告(P0 项)的收口，多端构建不在本切片。
- **关联证据**：`test/_03_contract_test/test_ffi_contract.py`（真实 .so 契约门禁，先红后绿：修复前 5/6 失败，修复后 7/7 通过）

## 根因与修复

1. **FFI 契约失配 ×4**（Dart 侧契约按内存 mock 定义，全部既有测试不经过真引擎通道）：
   - `doc.list` 裸数组 → 信封 Map `{books:[...]}`（`ffi.rs`），并注入真实 `sections_count`（`storage.rs count_sections`）；
   - 词云 action 名：`ffi.rs` 同时接受前端下单名 `nlp.keyword_extract` 与规范名 `nlp.extract_keywords`；
   - 词云字段：输出 `{word,score,count}`（映射自 `tfidf_score/frequency`）；
   - 导图字段：输出 `{id,label,depth,parent_id,section_id}`（映射自 `title/level`）。
2. **解析器诚实化**（`parser.rs` 重写）：PDF/EPUB 按 MVP 冻结范围显式拒绝（此前返回硬编码假正文入库）；MD/TXT 真实 SHA-256、真实字符偏移、按一级标题切分章节、读取失败显式报错（此前静默返回示例正文）。
3. **吞错链拆除**（`service.rs doc_parse`）：解析错误不再吞进 txt fallback；未知扩展名仍走显式 txt 兜底。
4. **数据完整性**：
   - `save_book` 改 `RETURNING id`——upsert 走 UPDATE 臂时 `last_insert_rowid()` 不推进，重复导入曾把派生数据挂到陈旧 id 上（FOREIGN KEY 失败此前被 `let _` 吞掉）；
   - `save_sections` 返回真实章节 id，句子外键回填（此前占位符只对库里第一本书碰巧成立）；
   - FEAT-001 去重：同哈希重复导入显式拦截；同路径换内容重建派生数据；关键词/关系/导图改为覆盖式保存（此前每次调用累积）。
5. **桥接显式降级**（`reader_engine_bridge.dart`）：真实引擎链路失败返回错误信封（50002），不再静默回退 mock；新增 `usesMockEngine`；书库运行时显示"演示模式"明示条（测试环境隐藏以保持 golden 基线）。
6. **前端口径**：导入对话框改为 MD/TXT；mock 示例书 EPUB→TXT；书库 golden 基线按内容修正重新生成。

## 回归证据

| 套件 | 结果 |
|---|---|
| `cargo test`（backend） | 34/34（含新增 3 个 parser 单测） |
| `test/_03_contract_test`（真实 .so，ctypes） | 7/7 |
| Flutter `flutter test` | 57/57（书库 golden 按内容修正重生成） |
| Python e2e / core / CLI | 4/4、8/8、4/4 |
| 性能基准 | 3/4（`test_02` NLP 关键词 174.9ms 超断言 100ms：环境敏感 + 断言比 SLA 标题更严，既有问题非本切片引入） |

## 遗留与登记

- 事件词态/术语重命名（`annotation.delete`→`.deleted` 等 7 项 verify_consistency 违规）：涉全调用面，按兼容性优先原则另行切片。
- Python 测试套件共享真实 `~/.ai-reader` DB 且偶发 Bus error：既有隔离缺陷，建议各套件改用临时 `AI_READER_HOME`。
- Flutter tester 在代理环境需 `no_proxy=127.0.0.1,localhost`（本机环境注入 `http_proxy` 会劫持 tester 本地取内核请求，表现为段错误）。
- 伴读轮询无取消、全局 Mutex 串行化、中文单字分词质量：P2 遗留（见探索报告）。

---

# 变更记录：CFX-002 Rust 引擎全旅程 e2e 补齐 + 配置读写路径错位修复

- **日期**：2026-10-25
- **intent / change_size / work_mode**：`FIX` / `S` / `IMPLEMENT`
- **触发**：开发者要求补齐真引擎端到端覆盖（GUI 层 e2e 受限于桌面工具链，先补引擎级全旅程）。

## 新增

`test/_00_e2e/test_rust_engine_full_flow_e2e.py`（5 用例，ctypes 驱动真实 .so，与 Python 引擎 e2e 形成双引擎对偶）：

1. 阅读旅程数据就绪：书库章节数 / 段落句子绑定真实章节 / 导图节点带 section_id / 词云非空；
2. 划词伴读双路径：流式 start→poll 收敛且空密钥标记 `offline=true`、离线卡带 `【离线模式】` 前缀（前端降级提示契约）+ 兜底阻塞 ask；
3. 批注全生命周期 save→list→update→list→delete→list；
4. 配置三通道：默认加载→部分保存→读回一致→落盘 `<base>/config/llm_config.json`；
5. 跨进程持久化：独立子进程（模拟重启）读回书库/批注/配置（探针走文件通道，规避引擎日志混流）。

隔离纪律：`AI_READER_HOME` + `HOME` 双重指向临时目录，不触碰宿主机真实数据。

## 顺带修复（e2e 首跑即抓到的真缺陷）

`LlmConfig::load()` 读旧版位置 `$HOME/.config/ai-reader/llm_config.json`，而 `config.save` 写集中存储位置 `<base>/config/llm_config.json`——**前端设置保存后重载读不回，LLM 密钥/参数重启即丢**（默认安装同样错位）。修复：load 优先读集中存储位置，旧位置仅作回退（保住升级用户已存密钥）。修复前该 e2e 用例为红，修复后转绿。

## 回归证据

| 套件 | 结果 |
|---|---|
| `cargo test` | 34/34 |
| 新增 Rust 引擎全旅程 e2e | 5/5（配置用例先红后绿） |
| FFI 契约测试 | 7/7 |

## 遗留与登记（新增）

- 阻塞 `ai.companion_ask` 的离线卡不带 `【离线模式】` 前缀（流式路径带）：老引擎兼容路径的引擎间文案漂移，前端主路径不受影响，建议统一。
- Python 引擎配置读取仍走旧版位置（其自身无 config.save 动作，暂无实际影响）：双引擎契约单源化的后续切片处理。
- GUI 层 e2e（Flutter integration_test 驱动真 .so）：需桌面构建工具链（clang/cmake/ninja/libgtk-3-dev），待环境具备后补。
