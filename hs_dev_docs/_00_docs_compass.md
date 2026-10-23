# 项目文档阅读说明与全局索引导航 (Project Documentation Reading Guide & Index)

> **项目名称**：`ai-reader`  
> **体系规格**：符合《产品开发 Skill 规格定义书 v2.4+》  
> **文档中枢根目录**：`hs_dev_docs/`  
> **倒排索引数据库**：`hs_dev_docs/_00_project_foundation/_05_doc_index/doc_index.sqlite`  
> **全局根索引**：`hs_dev_docs/_00_hs_dev_docs.idx`  
> **生成时间**：`2026-10-16T00:32:22Z`

---

## [VIBE_CONTRACT] 机器极速索引契约 (Machine-Actionable Index Manifest)
<!-- 
  【专供 AI Agent / LLM 极速切片检索（行 1～45）】
  说明：本区块为机器可解析的索引契约与快速检索指令集。外部 Agent 接入本系统时，
  优先执行以下专用检索子命令获取精准行段，绝对禁止对 hs_dev_docs 进行整目录扫描！
-->
```yaml
vibe_index_contract:
  docs_root: "hs_dev_docs"
  index_db_path: "hs_dev_docs/_00_project_foundation/_05_doc_index/doc_index.sqlite"
  root_idx_path: "hs_dev_docs/_00_hs_dev_docs.idx"
  dictionary_path: "hs_dev_docs/_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml"

  # 一级功能域与权威索引映射
  domain_routing:
    _00_project_foundation: "hs_dev_docs/_00_project_foundation/_00_project_foundation.idx"
    _01_product_vision: "hs_dev_docs/_01_product_vision/_00_product_vision.idx"
    _02_feature_spec: "hs_dev_docs/_02_feature_spec/_00_feature_spec.idx"
    _03_architecture_design: "hs_dev_docs/_03_architecture_design/_00_architecture_design.idx"
    _04_engineering_contract: "hs_dev_docs/_04_engineering_contract/_00_engineering_contract.idx"
    _05_task_orchestration: "hs_dev_docs/_05_task_orchestration/_00_task_orchestration.idx"
    _06_dev_process: "hs_dev_docs/_06_dev_process/_00_dev_process.idx"

  # Agent 极速检索 CLI（跨平台标准库执行，免扫全盘，Token 节省 90%+）
  agent_cli_shortcuts:
    feature_search: "python scripts/doc_index_db.py --root . feature-search --q <关键词>"
    page_search: "python scripts/doc_index_db.py --root . page-search --q <页面/功能>"
    pattern_search: "python scripts/doc_index_db.py --root . pattern-search --q <模式名>"
    schema_search: "python scripts/doc_index_db.py --root . schema-search --q <表名>"
    dep_graph: "python scripts/doc_index_db.py --root . dep-graph --symbol <类名.方法名>"
    method_search: "python scripts/doc_index_db.py --root . method-search --q <业务意图>"
    symbol_slice: "python scripts/doc_index_db.py --root . symbol-slice --name <符号名>"
    test_search: "python scripts/doc_index_db.py --root . test-search --q <方法/类名>"
    audit_search: "python scripts/doc_index_db.py --root . audit-search --since <YYYY-MM-DD>"
    embed_search: "python scripts/doc_index_db.py --root . embed-search --q <语义查询>"
    text_search: "python scripts/doc_index_db.py --root . search --q <关键词>"
    line_slice: "python scripts/doc_index_db.py --root . slice --path <相对路径> --start <行> --end <行>"

guardrails:
  - "FORBIDDEN: 严禁全量通读 hs_dev_docs 目录大文件（Token 预算硬性拦截）"
  - "MUST: 查阅代码与文档优先使用 doc_index_db 专属子命令进行局部切片"
  - "MUST: 跨 Agent 遵循统一术语单一事实源（_02_project_word.dict.yaml）"
  - "MUST: 代码与契约变更后必须执行 python scripts/doc_index_db.py --root . rebuild 自愈索引"
```

---

## 1. 文档体系核心架构与三层收敛漏斗

为解决复杂项目中 Agent 和人类工程师读取文档时的 Token 爆炸与盲目性，本体系构建了严格的**三层数据收敛漏斗**：

```text
[顶层 L2: 索引大脑]  doc_index.sqlite (FTS5 / 关键词倒排索引 / 毫秒级快速路由)
        │            ▲
        ▼            │ 【第 1 次收口：意图检索 (feature/page/schema/method-search)】
[中层 L1: 业务总结]  hs_dev_docs/ (接口契约 / 方法七维画像 / 模式集群 / 调用链路)
        │            ▲ 高信噪比派生视图，记录业务意图与符号锚点 (Symbol Anchor)
        ▼            │ 【第 2 次收口：契约锁定与符号定位】
[底层 L0: 物理真理]  7 大最底层数据资产 (产品原型 + 架构决策 + 源码 + DDL + 测试 + 配置 + 变更历史)
                     ▲ 【第 3 次收口：精准行段切片 (10~30 行)】
```

### 1.1 两级目录规约
整个 `hs_dev_docs` 严格遵循**两级目录规约**：一级功能域 `_00_` ~ `_06_` + 二级子功能原子拆分，严格遵循 `_01_xxx` 顺序命名规则，彻底消除深层任意嵌套，实现 `Domain + Category` 二元高信噪比精准检索与极速切片装配。

---

## 2. 全功能域直接索引导航目录表 (Direct Index Catalog)

以下为系统所有功能域及二级子域的直接索引表，点击相对路径直达对应目录或文件：

| 序号 | 功能域 | 相对路径 | 权威 .idx 索引 | 职责定位与核心产出物 |
|:---|:---|:---|:---|:---|
| **00** | **项目基座与全局规范**<br/>`_00_project_foundation` | [`_00_project_foundation/`](./_00_project_foundation/) | [`_00_project_foundation.idx`](./_00_project_foundation/_00_project_foundation.idx) | **系统底座与通用规则**<br/>• `_01_dev_rule`: 编码规范与 Lint 门禁<br/>• `_02_dictionary`: [`_02_project_word.dict.yaml`](./_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml) 统一术语单一事实源<br/>• `_03_decision_record`: 架构决策记录 (ADR)<br/>• `_04_code_map`: 代码地图与模块拓扑 (按需/SQLite 索引承载)<br/>• `_05_doc_index`: [`doc_index.sqlite`](./_00_project_foundation/_05_doc_index/doc_index.sqlite) 倒排索引数据库 |
| **01** | **产品愿景与分阶段定界**<br/>`_01_product_vision` | [`_01_product_vision/`](./_01_product_vision/) | [`_00_product_vision.idx`](./_01_product_vision/_00_product_vision.idx) | **业务意图第一因与阶段定界**<br/>• `_01_design_charter`: 品味宪章、物理隐喻与 Design Tokens (`DESIGN.md`)<br/>• `_02_phased_roadmap`: 分阶段路线图、MVP 激进裁剪决策书<br/>• `_03_business_plan`: 商业模式与核心业务假设 (可选/按需) |
| **02** | **特性规格与原型契约**<br/>`_02_feature_spec` | [`_02_feature_spec/`](./_02_feature_spec/) | [`_00_feature_spec.idx`](./_02_feature_spec/_00_feature_spec.idx) | **产品特性规格与人机双视图**<br/>• `_01_human_prd`: 面向人类的产品需求文档<br/>• `_02_vibe_spec`: 面向机器/VibeCoding的契约规格 (`vibe_spec.md`)<br/>• `_03_prototype_html`: 单文件零依赖可交互原型 (`{feature}_prototype.html`)<br/>• `_04_prototype_wireframe`: 空间拓扑与多端线框标注 |
| **03** | **系统架构设计与模式蓝图**<br/>`_03_architecture_design` | [`_03_architecture_design/`](./_03_architecture_design/) | [`_00_architecture_design.idx`](./_03_architecture_design/_00_architecture_design.idx) | **工程结构第一因与模式协同**<br/>• `_01_system_architecture`: 整体架构与分层蓝图<br/>• `_02_pattern_clusters`: GoF 设计模式协同集群档案与防破坏指针<br/>• `_03_adapter_spec`: 第三方/专用 SDK 防腐适配层规范 |
| **04** | **工程四要素详细契约**<br/>`_04_engineering_contract` | [`_04_engineering_contract/`](./_04_engineering_contract/) | [`_00_engineering_contract.idx`](./_04_engineering_contract/_00_engineering_contract.idx) | **工程实现物理契约真理**<br/>• `_01_db_schema`: 数据库表结构、DDL 与迁移基线 ([`_00_db_schema.idx`](./_04_engineering_contract/_01_db_schema/_00_db_schema.idx))<br/>• `_02_interface_design`: RESTful/RPC 接口契约 ([`_00_interface_design.idx`](./_04_engineering_contract/_02_interface_design/_00_interface_design.idx))<br/>• `_03_mock_contract`: Mock 数据契约与 Profile<br/>• `_04_method_design`: 方法七维画像与测试矩阵 ([`_00_method_design.idx`](./_04_engineering_contract/_04_method_design/_00_method_design.idx))<br/>• `_05_call_chain`: 核心调用链与时序拓扑 ([`_00_call_chain.idx`](./_04_engineering_contract/_05_call_chain/_00_call_chain.idx)) |
| **05** | **任务编排与上下文装配**<br/>`_05_task_orchestration` | [`_05_task_orchestration/`](./_05_task_orchestration/) | [`_00_task_orchestration.idx`](./_05_task_orchestration/_00_task_orchestration.idx) | **敏捷工程交付与上下文装载**<br/>• `_01_task_brief`: 任务简述清单 ([`_00_task_brief.idx`](./_05_task_orchestration/_01_task_brief/_00_task_brief.idx))<br/>• `_02_task_detail`: 任务状态机详述 ([`_00_task_detail.idx`](./_05_task_orchestration/_02_task_detail/_00_task_detail.idx))<br/>• `_03_task_context_pack`: 编译装配的高信噪比上下文包 ([`_00_context_pack.idx`](./_05_task_orchestration/_03_task_context_pack/_00_context_pack.idx))<br/>• `_04_task_archive`: 历史已完成任务归档 ([`_00_task_archive.idx`](./_05_task_orchestration/_00_task_archive.idx)) |
| **06** | **开发过程与治理审计**<br/>`_06_dev_process` | [`_06_dev_process/`](./_06_dev_process/) | [`_00_dev_process.idx`](./_06_dev_process/_00_dev_process.idx) | **过程账本与抗脆弱回滚镜像**<br/>• `_01_plan_log`: 计划与里程碑日志<br/>• `_02_change_log`: 变更流水账本 (非 Git 物理回滚依据)<br/>• `_03_verify_log`: 测试与一致性验证审计记录 (按需)<br/>• `_04_error_recovery`: 故障恢复与快照 (Snapshots)<br/>• `_05_tech_debt`: 技术债务清单与还债规划 (按需) |

---

## 3. 其他 Agent 极速索引与检索操作手册 (Agent Query Playbook)

当任何协同 Agent（如 Claude、GPT-4o、DeepSeek、Gemini 或其他 IDE 插件）介入本项目时，**严禁使用全量递归搜索或大段通读**。必须通过标准库支持的跨平台 CLI 专属命令进行毫秒级切片召回：

### 3.1 检索矩阵速查
| 检索场景 | 目标内容 | 推荐 CLI 指令 | 预期返回 |
|---|---|---|---|
| **查业务功能/需求** | PRD 契约、特性描述 | `python scripts/doc_index_db.py --root . feature-search --q "支付"` | 匹配特性 ID、标题、摘要及文件路径 |
| **查交互页面/线框** | 页面拓扑、线框规范 | `python scripts/doc_index_db.py --root . page-search --q "结算台"` | 页面路由、布局结构与线框图切片 |
| **查架构模式/集群** | 设计模式、防破坏护栏 | `python scripts/doc_index_db.py --root . pattern-search --q "Strategy"` | 协同方法列表、单向指针与安全护栏 |
| **查数据表/DDL** | 字段定义、表结构约束 | `python scripts/doc_index_db.py --root . schema-search --q "orders"` | 字段字典、索引设计与 DDL 迁移路径 |
| **查方法依赖拓扑** | 爆炸半径、调用时序 | `python scripts/doc_index_db.py --root . dep-graph --symbol "OrderService.create"` | 上游调用者（爆炸半径）与下游依赖 Mermaid 图 |
| **写前意图防膨胀** | 查重防重复造轮子 | `python scripts/doc_index_db.py --root . method-search --q "计算税费"` | 重合度 ≥80% 强制复用已有方法画像 |
| **精准源码切片** | AST 符号物理实现 | `python scripts/doc_index_db.py --root . symbol-slice --name "OrderService"` | 类/函数的精确起止行号与纯净源码 |
| **查测试用例单跑** | 单元测试、执行命令 | `python scripts/doc_index_db.py --root . test-search --q "test_pay"` | 自动化测试单跑命令与测试说明 |
| **查变更过程账本** | 物理回退与断点快照 | `python scripts/doc_index_db.py --root . audit-search --since "2026-10-14"` | 时间段内的文件修改历史与快照哈希 |
| **语义向量混合搜索** | 跨自然语言/代码意图 | `python scripts/doc_index_db.py --root . embed-search --q "幂等更新"` | 相似度加权排序切片清单 |
| **文档局部切片** | 任意设计文档行段 | `python scripts/doc_index_db.py --root . slice --path "hs_dev_docs/..." --start 1 --end 40` | 指定文档的高信噪比片段，杜绝全篇灌入 |

---

## 4. 意图驱动的 Agent 推荐阅读路径 (Scenario Reading Pathways)

协同 Agent 在开始执行具体任务时，应根据当前意图（Intent）按序阅读文档：

```text
[BUILD (从零构建)]
  └─► _01_product_vision (产品愿景/DESIGN.md)
        └─► _02_feature_spec (PRD / vibe_spec / 原型)
              └─► _03_architecture_design (ADR / 架构蓝图)
                    └─► _04_engineering_contract (DB / API / 方法设计)
                          └─► _05_task_orchestration (编译装配 Context Pack) ──► 编码与单测

[EXPLORE (只读理解)]
  └─► _00_project_foundation/_05_doc_index (CLI 检索定位)
        └─► symbol-slice / dep-graph (局部符号切片与依赖图)
              └─► 结构化输出业务时序或架构图谱 (纯只读免交付)

[FIX (Bug修复)]
  └─► audit-search / dep-graph (排查近期变更与影响范围)
        └─► _04_engineering_contract/_04_method_design (查阅方法契约与边界画像)
              └─► 编写最小复现用例 RED ──► 精准修复 GREEN ──► 回归门禁

[REFACTOR (等价重构)]
  └─► dep-graph (评估下游被调方与爆炸半径)
        └─► pattern-search (确认设计模式防破坏约束)
              └─► 固化特性测试保护网 ──► 消除坏味道 ──► 零行为漂移验证

[RESUME (任务续做)]
  └─► _06_dev_process/_01_plan_log & _02_change_log (执行 process_log.py resume-scan)
        └─► _05_task_orchestration/_02_task_detail (恢复当前在制品断点) ──► 沿既有 Plan 继续
```

---

## 5. Agent 协同与防漂移治理铁律 (Guardrails & Anti-Drift Policy)

1. **统一语言与单一事实源 (Ubiquitous Language)**：
   所有业务实体、字段命名、事件名称必须与 [`_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml`](./_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml) 保持绝对一致。严禁发明近义词或裸字符串。
2. **符号锚点防漂移 (Symbol Anchor)**：
   设计文档和任务包中绝对禁止硬编码绝对物理代码行号。必须使用 `Symbol Anchor`（如 `OrderService.createOrder#validation`），由底层的 AST 符号切片引擎动态求值行号。
3. **机器契约优先 (Machine Contract First)**：
   AI 编码与装配时，优先读取各文档顶部带有 `[VIBE_CONTRACT]` 标记的切片区块（行 1～35），杜绝下半部冗长的人类背景论证挤占 Token。
4. **索引自动同步机制 (Self-Healing Index)**：
   批量新增或更新设计文档后，必须执行以下指令保证权威 `.idx` 与 SQLite 缓存同步：
   ```bash
   python scripts/doc_index_db.py --root . rebuild
   ```
