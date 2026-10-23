# 阶段 0 冻结确认单：AI Reader 沉浸式 AI 认知阅读器（MVP / Phase 1）

- **编制日期**：2026-10-16
- **修订版本**：`v1.1`（首轮评审 REJECTED → 按完整清单整改 P1–P6 / D1–D7，见 `qa_log_002_phase0_freeze_revision.md`）
- **intent / change_size / work_mode**：`BUILD` / `L` / `DESIGN`
- **冻结对象**：阶段 0 产品设计（宏观品味宪章 + MVP 内功能规格 + 双轨原型 + 分阶段规划书）
- **对应任务**：`task_000_bootstrap_rebuild`（从零重写重建）
- **决策日志**：`_06_dev_process/_03_qa_log/qa_log_001_bootstrap_mvp_scope.md`、`qa_log_002_phase0_freeze_revision.md`、`qa_log_003_phase0_freeze_verification.md`
- **模板来源**：`hs-dev-skill/resources/templates/process/freeze_signoff.md`

> 阶段 0 冻结（进入阶段 1 技术选型）前必须由开发者签署本单。**视觉签收（原型 6 项检查）只代表「好看」，不代表「业务对」——业务语义必须逐条勾选确认。**

---

## A. 业务语义签收（逐条确认，缺一不可）

- [ ] **核心场景与反目标**：与 PRD 一致，无误解
  - 核心场景：`导入 Markdown/TXT → 解析入库 → 版心渲染 → 划词 → 认知模板流式伴读 → 原位追问 → 一键存为边注 → 回看导图/词云`。
  - 反目标（Hard Non-Goals）：不做 PDF/EPUB、不做 iOS/macOS、不做账号/云同步/云端 LLM 代理、不做多设备协作、不做任何后台管理台。
- [ ] **权限 / 计费 / 归属 / 审计规则**：与预期一致
  - 本地单用户应用，唯一角色 `ROLE_READER`；无登录/多角色/权限体系；无计费；数据归属本机用户，全部落于 `~/.ai-reader`；运行期日志脱敏、LLM 密钥不回显明文。
- [ ] **核心交互主路径与流程**：路由 / 状态流转无异议
  - 主路径与四大特性状态机（`companion_stream` 的 `IDLE→REQUESTING→STREAMING→DONE→SAVED`、聚焦模式、导入、标注）已逐条核对，见各 `vibe_spec.md` 的 `state_machine`。
- [ ] **业务规则矩阵与边界异常**：默认值、边界、极端情况符合预期
  - 关键边界：LLM 未配置 / 断网 / 超时 → 退避重试后本地启发式降级（<10ms）并标注「离线降级」；解析失败 → 明确报错且不丢草稿；「存为边注」幂等；标注 7 样式 × 调色板；正文版心 700px；零 emoji。
- [ ] **Gherkin DoD 逐条可测**：Given/When/Then 覆盖主成功流、校验流、异常恢复流
  - 11 份 `vibe_spec.md` 的 `executable_tests_gherkin` 已覆盖主成功流（TEST-01）、校验流、异常恢复流（TEST-03 降级 / TEST-04 幂等）；阶段 5 将逐条转为可执行测试。
- [ ] **MVP 范围**：MVP 功能边界已由开发者裁定
  - MVP = `FEAT-001`~`FEAT-011`（含导图/词云、AI 键盘、标注多风格）；主交付平台 = Linux + Windows + Android。非 MVP（`FEAT-012`~`FEAT-017`）仅登记 MoSCoW 池，不写详细规格。
- [ ] **DB 设计（如触达）**：新增表 / 改表 / 迁移已由开发者决策确认（硬性，不可跳过）
  - 开发者已于 Q5 **授权**按阶段 3 设计稿建表（含标准审计字段 `id/created_at/updated_at/description/is_del/version`）与 V/U 迁移；后续任何新增/破坏性表变更仍需再次开发者决策。

---

## B. 视觉签收（原型 6 项检查）

> 依据：`DESIGN.md` + `_02_feature_spec/_03_prototype_html/ai_reader_prototype.html`（零依赖单文件，双击直读）+ `_04_prototype_wireframe/*.md`（Mermaid 拓扑 + ASCII 比例线框）。

- [ ] 布局与容器结构明确：桌面三栏（目录 260 / 版心 700 / 伴读 440）、书库容器 1120px、移动端单栏 + Bottom Sheet。
- [ ] 字体与字阶层级完整（含 tabular-nums）：Reader Body `iA Writer Duo` 19/1.7、Mono `iA Writer Mono` 12、UI Sans `Inter` 14；页码/字数/TTFT 强制 `tabular-nums`。
- [ ] 间距与 Design Tokens 一致：4/8 基阶（4/8/16/24/32）；圆角级差 6/8/12/20；单一品牌强调色 `#007AFF` 首屏预算 ≤3 处。
- [ ] 终端平台交互特性合规（桌面/移动/Web）：桌面 `Cmd+*` 快捷键 + 44px 顶栏隐退；Android 长按划词药丸 + 半屏 Bottom Sheet + ≥44px 触达 + safe-area。
- [ ] 页面四态无死角（Empty / Loading / Populated / Error）：书库空态引导、解析骨架、伴读流式占位与降级/报错态均已标注。
- [ ] 工程实现可映射（可直接转为组件树 + CSS Variables）：`vibe_spec` 已给出 `component_tree` + `design_tokens.css_variables`，可直接映射 Flutter Widget 树与 Theme。

> **v1.1 整改实证（原型，详见 `qa_log_003`）**：① 零外部依赖——跨源请求 = **0**、资源条目 = **0**、控制台消息 = **0**（无 CDN / 无外部字体，断网可用）；② 真实闭环——划词 → 就近胶囊 → 逐字流式（含实测 TTFT）→ 原位追问 → 存为边注（幂等）→ 标注列表即时新增，CDP 驱动 **8/8 断言 PASS**；③ `scripts/anti_slop_check.py` 静态 8 项全 PASS（#4/#8 为运行态按屏实测：强调色 ≤1/屏，对比度 浅 17:1、暗 17:1）；④ 修复 P2 闭环回归 `R-01`（`startCompanion` 未切界面）。

---

## C. 冻结确认

- [ ] 一源双视图（PRD + vibe_spec）齐套且无语义冲突（11 特性 × PRD + 11 × vibe_spec = 22 份）。
- [ ] 分阶段规划书落盘且源自审讯结论（`_01_product_vision/_02_phased_roadmap/ai_reader_phased_plan.md`；MVP 范围已裁定）。
- [ ] Q&A 决策日志（`_06_dev_process/_03_qa_log/qa_log_001_bootstrap_mvp_scope.md`）已记录关键问答与拍板。

---

## D. Agent 10 维产品与体验自审标尺（自动自审，非签收主体）

> 依据 Skill `product_design.md` §5.1。自审通过仅为冻结前置条件，**签收以开发者 A/B/C 部分为准**。

| # | 自审维度 | 结论 | 证据锚点 |
|---|---|---|---|
| 1 | 宏观品味合规（`DESIGN.md` + 显式继承） | PASS | 根 `DESIGN.md`；11 份 PRD 均声明 `Inherits: /DESIGN.md` |
| 2 | 痛点与 JTBD 真伪（Status Quo 已写清） | PASS | `overview_prd.md` §1/§6；`DESIGN.md` Overview |
| 3 | Aha Moment 与冷启动 FTUE（3 步内） | PASS | `library_import_prd.md` 空态引导 → 划词胶囊 → 伴读卡片；原型四态 |
| 4 | 方案博弈（核心交互 ≥2 形态 Trade-offs） | PASS | 胶囊 vs 全局面板/AI 键盘；半屏 Bottom Sheet vs 全屏；已记录取舍 |
| 5 | 渐进式披露与视觉动线（唯一主视觉锚点） | PASS | 正文版心为唯一主视觉；顶栏 3s 隐退；强调色预算 ≤3 |
| 6 | 双轨原型表现力（Mermaid + ASCII 线框） | PASS | `_04_prototype_wireframe/*.md` 11 份 + 单文件 HTML 原型 |
| 7 | 页面四态与组件六态（保留已填草稿） | PASS | 原型四态仿真；`companion_stream` error 态 `preserveSelection: true` |
| 8 | 真实微文案（具象动词、零 Lorem） | PASS | 按钮「存为边注/原位重试」；报错均附人话修复指引 |
| 9 | Gherkin 验收标准（Given/When/Then 可观测） | PASS | 11 份 `vibe_spec` 的 `executable_tests_gherkin` |
| 10 | 绝对纯净无技术污染（PRD 剔除 DDL/签名/覆盖率） | PASS | 阶段 0 文档无表 DDL / 无 RPC 签名 / 无覆盖率指标 |

**自审结论**：10/10 通过，满足阶段 0 冻结门禁前置条件。

> 反 AI 皮落地：`scripts/anti_slop_check.py`（静态 8 项，#4/#8 运行态按屏实测）；原型跨源请求 = 0；CDP 30+ 交互断言 PASS。

---

## E. 冻结门禁复核表（Skill `product_design.md` §5.2）

| 校验维度 | 通过条件 | 状态 |
|---|---|---|
| 宏观品味宪章就绪 | 根 `DESIGN.md` 存在且含隐喻/Tokens/Anti-Slop | 通过 |
| 一源双视图齐套 | 11 × PRD(+双轨原型) + 11 × vibe_spec，均继承 DESIGN.md | 通过 |
| 产品探索与方案比选完备 | Status Quo / JTBD / Aha / FTUE / ≥2 形态取舍 | 通过 |
| 功能与双轨交互完备 | 架构树 + 端到端旅程 + 双轨原型四态 + Gherkin DoD | 通过 |
| MVP 范围已裁定 | Q1/Q2/Q3 已拍板，分阶段规划书落盘 | 通过 |
| 业务语义签收 | 开发者逐条确认（本单 A 部分） | 待签收 |
| 纯净无技术侵入 | 阶段 0 文档零底层选型/DDL/RPC 签名 | 通过 |
| 无冲突一致性 | 文档互引无矛盾，术语词典已重建为 AI Reader 领域词表 | 通过 |

---

## F. 已记录的遗留门禁项（不阻断冻结，阶段 5/6 收口）

1. **术语词典已重建**：`_02_project_word.dict.yaml` 由 Skill 模板（订单/支付域）重写为 AI Reader 领域统一语言（`book/section/sentence/annotation/margin_note/cognitive_template/conversation/message/keyword/mindmap_node/reading_progress/...`），并采用保守 `forbidden_alias`（排除 `release/change/make/remove` 等与构建系统冲突的通用词），已消除全部构建产物误报。
2. **遗留代码违规 7 项（阶段 5 随重写清零）**：`verify_consistency --root .` 当前 7 项错误，全部位于待重写的旧 `backend/` 代码——
   - 术语漂移 2 项：`backend/reader_engine.py`、`backend/src/ffi.rs` 使用缩写别名 `annot`（须改回 `annotation`）；
   - 事件词态 5 项：`reader_engine.py` 的 `doc.delete`/`book.delete`/`annotation.delete`、`ffi.rs` 的 `annotation.delete`/`annotation.update` 违反「Event 必须过去分词」硬规则（须改为 `.deleted`/`.updated`，且 `doc` → `book` 统一实体名）。
3. **工程脚本同步**：项目 `scripts/` 已同步为当前 Skill 版（新增 `doc_index_db.py` / `process_log.py` / `version_tool.py` / `governance_toggle.py` 等），支撑索引检索与过程账本；并新增 `scripts/anti_slop_check.py`（DESIGN.md Anti-Slop 10 项的机械自检器）。
4. **文档层零 emoji 归一**：全量 `hs_dev_docs` 已按「零 emoji」归一（emoji 字形 → 排版字符或文字）；`DESIGN.md` 符号语言封闭枚举新增 `≡`（目录/菜单，U+2261），Anti-Slop #2 明确豁免功能性焦点环阴影。

---

## G. 返工整改记录（v1.0 → v1.1，首轮评审 REJECTED 后）

> 依据 `qa_log_002_phase0_freeze_revision.md` §2 的 13 项缺陷（原型 P1–P6 + 宪章 D1–D7），全部采纳、不降级、不延后。

| 编号 | 缺陷摘要 | 落盘位置 | 验收证据 |
|---|---|---|---|
| P1 | 原型依赖 CDN（Tailwind/Google Fonts） | `prototype_html/ai_reader_prototype.html` 重写为零依赖单文件 | 跨源请求 = 0；手写 CSS + 系统字体栈 |
| P2 | 「可交互」实为静态贴图 | 同上：真实状态机 `S` + `render()` | 划词→胶囊→流式→追问→存边注→列表新增闭环，30+ 断言 PASS |
| P3 | 表面覆盖缺口（三端/导入/聚焦/高级参数/Esc） | 原型新增 9 界面 + 导入对话框 + 三端分发页 | 4 态 × 明暗 × 9 界面直读；Esc 分层关闭 |
| P4 | 导图无连线、毛玻璃未真呈现 | 原型：SVG 连线 + 真实 `.frost` 遮罩层 | 视觉复核通过 |
| P5 | 无 `focus-visible` / `reduced-motion` / 触达尺寸 | 原型 + `DESIGN.md` 状态动效契约 | `:focus-visible` 绘制焦点环；`prefers-reduced-motion` 全 0ms；≥44px |
| P6 | 微文案残留英文、符号不统一 | 原型 + `DESIGN.md` 符号语言 | 全部中文微文案；符号封闭枚举 |
| D1 | 字体落地矛盾、缺 CJK 配对与三端回退矩阵 | `DESIGN.md` 字体矩阵 | Reader/Mono/UI 三栈 + 三端回退 |
| D2 | 暗色主题只有变量、无规则 | `DESIGN.md` 暗色规则 | highlight/对比度/强调色切换规则 |
| D3 | Anti-Slop 缺「机械自检项」 | `DESIGN.md` 10 项表 + `scripts/anti_slop_check.py` | 静态 8 项全 PASS |
| D4 | 缺状态与动效规范 | `DESIGN.md` 状态/动效契约 | hover/active/disabled/focus-visible + reduced-motion |
| D5 | 缺符号与空态语言 | `DESIGN.md` 封闭枚举 | 三行空态结构 + 符号白名单 |
| D6 | 缺 Android 特有规则 | `DESIGN.md` Android 规则 | Sheet 阈值/长按时长/返回手势/safe-area |
| D7 | Markdown 元素排版规格缺失 | `DESIGN.md` 内容排版规格 | 引用/代码/列表/分隔线/链接/表格/图片 |

---

> **冻结结论**：`APPROVED`（可进入阶段 1 选型）/ `REJECTED`（回切 DESIGN）
>
> **当前状态**：`PENDING` — 待开发者签署
>
> **开发者签名**：__________ **日期**：__________
