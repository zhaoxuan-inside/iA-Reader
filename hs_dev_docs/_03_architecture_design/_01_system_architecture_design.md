# AI Reader 全系统架构设计规范 (System Architecture Design)

**文档编号**：ARCH-001  
**生命周期阶段**：阶段 2 - 领域建模与架构设计  
**编写时间**：2026-10-10  
**状态**：APPROVED (Headless Core Engine)

---

## 1. 总体架构分层视图 (Clean Architecture / DDD 分层)

系统采用经典的整洁架构（Clean Architecture）四层模型，以纯 Headless 核心计算与解析引擎为中心，提供命令行 CLI 与标准跨语言 C-ABI FFI 入口：

```text
+---------------------------------------------------------------------------------------+
|                                接入调度层 (Ingress & Interface Layer)                  |
|  - 命令行交互终端: AI Reader CLI (argparse, 格式化输出, parse, keywords, graph, ask)    |
|  - 跨语言桥接接口: ai_reader_invoke C-ABI FFI (JSON invoke_envelope, 统一错误码与度量) |
+-------------------------------------------|-------------------------------------------+
                                            | 调度请求 / 载荷分发
+-------------------------------------------v-------------------------------------------+
|                           应用编排层 (Application Layer - Core Engine)               |
|  - DocService: 文档解构与段落分块编排                                                |
|  - NlpService: 全文/章节/句子分词与共现计算编排                                      |
|  - MindmapService: AST 导图提取与层级树构建编排                                       |
|  - AnnotationService: 批注增量管理与 Markdown 导出编排                               |
|  - AiService: 认知模板装配、流式调用与离线启发式降级编排                             |
+-------------------------------------------|-------------------------------------------+
                                            |
+-------------------------------------------v-------------------------------------------+
|                           领域模型层 (Domain Layer - Domain Model)                   |
|  - 聚合根: BookAggregate, AnnotationAggregate, ConversationAggregate                 |
|  - 实体: BookMeta, BookSection, SentenceNode, KeywordNode, MindmapNode               |
|  - 值对象: TextAnchor, KeywordRelation, BoundingBox, CognitiveTemplateType           |
|  - 领域算法: JiebaTokenizer, TfidfScorer, TextRankEngine, PmiCoOccurrenceCalculator  |
+-------------------------------------------|-------------------------------------------+
                                            |
+-------------------------------------------v-------------------------------------------+
|                          基础设施层 (Infrastructure Layer - Storage & Parsers)        |
|  - 存储适配器: SqliteStorage (WAL模式, 强制审计字段与前向/回滚迁移)                   |
|  - 解析适配器: PdfParser, EpubParser, MarkdownParser, TxtParser                        |
|  - 外部服务适配器: LlmClient (SSE 流式传输, 离线启发式 Mock 隔离, 指数退避重试)       |
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
1. **输入**：CLI 命令或 FFI 传入文档路径（`file_path`）；
2. **解构**：`DocService` 路由至对应格式解析器（PDF/EPUB/MD/TXT），解析出 `BookMeta`、`Vec<BookSection>`、`Vec<SentenceNode>`；
3. **入库**：写入 SQLite 本地库（原子事务保障）；
4. **离线 NLP**：`NlpService` 触发分词与打分，抽取全局关键词并生成 `KeywordRelation` 共现网络；
5. **导图构建**：`MindmapService` 提取目录树生成 `MindmapNode` 树；
6. **响应**：返回结构化 `BookMeta` 与段落统计指标。

### 3.2 选区伴读与批注沉淀流程 (AI Companion Flow)
1. **触发**：传入目标文本或段落选区；
2. **模板选择**：选择认知模板（如“逻辑链剖析”）；
3. **上下文装配**：`AiService` 自动装配当前句子、所属章节前后上下文与核心关键词列表；
4. **流式生成**：流式调用 LLM 获取解析结果（离线时自动降级输出思维启发卡）；
5. **沉淀保存**：保存至 SQLite `annotation` 与 `ai_conversation` 表。

---

## 4. 关键架构非功能保障与设计准则

1. **六元组运行时准则**：所有业务方法严格规范主方法、补偿（`_compensate`）、降级（`_fallback`）、度量（`_metrics`）与回调（`_recall`）；
2. **纯本地离线优先**：文档解析、文本检索、分词打分、思维导图、历史书架均 100% 本地运算，无网络时外部 AI 伴读自动降级为本地预置思维启发卡片；
3. **数据完整性保障**：SQLite 开启 WAL 日志模式，所有修改操作具备 `version` 乐观锁控制与 `is_del` 软删除机制。
