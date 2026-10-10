# AI Reader 全系统架构设计规范 (System Architecture Design)

**文档编号**：ARCH-001  
**生命周期阶段**：阶段 2 - 领域建模与架构设计  
**编写时间**：2026-10-10  
**状态**：APPROVED  

---

## 1. 总体架构分层视图 (Clean Architecture / DDD 分层)

系统采用经典的四层架构，并结合 Flutter 展现层与 Rust 核心计算引擎的跨语言特性进行严格隔离：

```text
+---------------------------------------------------------------------------------------+
|                                展现层 (Presentation Layer - Flutter/Dart)               |
|  - 页面与路由: ShelfPage (书架), ReaderPage (双模阅读), GraphPage (图谱), MindmapPage  |
|  - 交互组件: iA Writer Margin 边注组件, 选区浮动胶囊, 4大伴读卡片, 力导向拓扑画布       |
|  - 状态管理: BookStateNotifier, ReaderController, AnnotationProvider, AIStreamNotifier|
+-------------------------------------------|-------------------------------------------+
                                            | FFI C-ABI (invoke_envelope)
+-------------------------------------------v-------------------------------------------+
|                           应用编排层 (Application Layer - Rust Engine)               |
|  - DocService: 文档解构与段落分块编排                                                |
|  - NlpService: 全文/章节/句子分词与共现计算编排                                      |
|  - MindmapService: AST 导图提取与折叠同步编排                                         |
|  - AnnotationService: 边注增量管理与 Markdown 导出编排                               |
|  - AiService: 认知模板装配、流式调用与离线降级编排                                   |
+-------------------------------------------|-------------------------------------------+
                                            |
+-------------------------------------------v-------------------------------------------+
|                           领域模型层 (Domain Layer - Pure Rust)                       |
|  - 聚合根: BookAggregate, AnnotationAggregate, ConversationAggregate                 |
|  - 实体: BookMeta, BookSection, SentenceNode, KeywordNode, MindmapNode               |
|  - 值对象: TextAnchor, KeywordRelation, BoundingBox, CognitiveTemplateType           |
|  - 领域算法: JiebaTokenizer, TfidfScorer, TextRankEngine, PmiCoOccurrenceCalculator  |
+-------------------------------------------|-------------------------------------------+
                                            |
+-------------------------------------------v-------------------------------------------+
|                          基础设施层 (Infrastructure Layer - Rust & SQLite)            |
|  - 存储适配器: SqliteStorage (rusqlite, WAL模式, 强制审计字段与前向/回滚迁移)          |
|  - 解析适配器: PdfParser (lopdf), EpubParser (epub), MarkdownParser (pulldown-cmark)  |
|  - 外部服务适配器: LlmClient (Reqwest/SSE 流式传输, 离线 Mock 隔离, 指数退避重试)     |
+---------------------------------------------------------------------------------------+
```

---

## 2. 限界上下文与上下文映射 (Bounded Contexts & Context Map)

系统划分 5 大高内聚、低耦合的限界上下文：

```mermaid
flowchart TD
    subgraph DocumentContext [1. 文档核心上下文 (Document Context)]
        BookMeta[BookMeta 聚合根]
        BookSection[BookSection 实体]
        SentenceNode[SentenceNode 实体]
    end

    subgraph NlpGraphContext [2. NLP与概念图谱上下文 (NLP Graph Context)]
        KeywordNode[KeywordNode 实体]
        KeywordRelation[KeywordRelation 值对象]
        CoOccurrenceMatrix[共现矩阵计算器]
    end

    subgraph MindmapContext [3. 思维导图上下文 (Mindmap Context)]
        MindmapNode[MindmapNode 树实体]
        AstConverter[目录树转换器]
    end

    subgraph AnnotationContext [4. 批注与边注上下文 (Annotation Context)]
        Annotation[Annotation 聚合根]
        TextAnchor[TextAnchor 空间坐标值对象]
    end

    subgraph AiCompanionContext [5. AI认知伴读上下文 (AI Companion Context)]
        AiConversation[AiConversation 聚合根]
        CognitiveTemplate[CognitiveTemplate 模板值对象]
        PromptAssembler[PromptContext 装配器]
    end

    DocumentContext -->|提供章节与句子AST| NlpGraphContext
    DocumentContext -->|提供目录树结构| MindmapContext
    DocumentContext -->|提供段落基线锚点| AnnotationContext
    DocumentContext -->|提供选区切片全文上下文| AiCompanionContext
    AnnotationContext -->|批注历史与问答联动| AiCompanionContext
```

---

## 3. 核心业务数据流转全景 (Data Flow Architecture)

### 3.1 文档导入与全书索引构建流程 (Doc Import Flow)
1. **输入**：用户选择文件路径（`file_path`）；
2. **解构**：`DocService` 路由至对应格式解析器（PDF/EPUB/MD/TXT），解析出 `BookMeta`、`Vec<BookSection>`、`Vec<SentenceNode>`；
3. **入库**：写入 SQLite 本地库（原子事务保障）；
4. **离线 NLP**：`NlpService` 异步触发分词与打分，抽取全局关键词并生成 `KeywordRelation` 共现网络；
5. **导图构建**：`MindmapService` 提取目录树生成 `MindmapNode` 树；
6. **响应**：通过 FFI 返回 `BookMeta` 及就绪状态给 Flutter 前端渲染书架卡片。

### 3.2 选区伴读与 iA Writer 边注沉淀流程 (Margin AI Companion Flow)
1. **触发**：读者选中文本段落，选区上标 `[※]` 锚点生成 `TextAnchor`；
2. **模板选择**：选择“逻辑链剖析”认知模板；
3. **上下文装配**：`AiService` 自动装配当前句子、所属章节前后 3 个段落、当前章节的核心关键词列表；
4. **流式生成**：通过 SSE 流式接收 LLM 输出，并在 Flutter 边注栏与原文段落基线平滑垂直对齐展示；
5. **沉淀保存**：用户点击“沉淀为边注”，原子入库 SQLite `annotation` 表。

---

## 4. 关键架构非功能保障与设计准则

1. **六元组运行时准则**：所有业务方法严格规范主方法、补偿（`_compensate`）、降级（`_fallback`）、度量（`_metrics`）与回调（`_recall`）；
2. **纯本地离线优先**：文档解析、文本检索、分词打分、思维导图、历史书架均 100% 本地运算，无网络时仅外部 AI 伴读降级为本地预置思维启发卡片；
3. **数据完整性保障**：SQLite 开启 WAL 日志模式，所有修改操作具备 `version` 乐观锁控制与 `is_del` 软删除机制。
