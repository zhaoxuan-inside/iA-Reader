# AI Reader 核心六元组方法设计规范 (Six-Tuple Method Design)

**文档编号**：METHOD-001  
**生命周期阶段**：阶段 3 - 详细规格设计  
**编写时间**：2026-10-10  
**状态**：APPROVED  

---

## 1. 六元组方法标准规范

依据 `hs-dev-skill` 标准，每个关键业务操作均需实现主方法与 5 个标准化衍生契约：
1. **主方法 (`method_name`)**：标准正向业务链路，包含参数校验与原子操作；
2. **Saga 补偿 (`method_name_compensate`)**：链路中断或事务回滚时的逆向补偿动作；
3. **熔断降级 (`method_name_fallback`)**：不可抗力、外部服务故障或超时时的轻量级降级兜底；
4. **度量指标 (`method_name_metrics`)**：记录调用延时、内存开销与吞吐指标；
5. **异步回调 (`method_name_recall`)**：操作成功后的后续事件分发或联动钩子。

---

## 2. 核心方法清单与衍生实现设计

### 2.1 文档解构方法组：`doc_parse`
- `doc_parse`: 主方法，根据文件后缀分发解析器（PDF/EPUB/MD/TXT），解析章节 AST 与句子节点并原子落库；
- `doc_parse_compensate`: 逆向补偿，如果入库中途异常，删除已插入的章节与句子并重置文件元数据；
- `doc_parse_fallback`: 降级策略，复杂格式解构失败时降级为纯文本按行切片流式解析；
- `doc_parse_metrics`: 收集解析耗时、段落数、文本总字数等度量信息；
- `doc_parse_recall`: 解析完成后触发，异步派发文档入库事件，驱动后台 NLP 分词。

### 2.2 关键词提取方法组：`nlp_keyword_extract`
- `nlp_keyword_extract`: 主方法，调用 Jieba 分词与 TF-IDF/TextRank 双重打分算法计算三级关键词；
- `nlp_keyword_extract_compensate`: 补偿方法，清理失败批次的关键词中间数据；
- `nlp_keyword_extract_fallback`: 降级策略，词频统计降级为简单的空格/标点粗粒度统计前 20 词；
- `nlp_keyword_extract_metrics`: 统计分词总词数、耗时与内存开销；
- `nlp_keyword_extract_recall`: 关键词抽取完毕后触发共现拓扑矩阵构建。

### 2.3 概念图谱构建方法组：`keyword_graph_build`
- `keyword_graph_build`: 主方法，基于滑动窗口计算词间共现频次与互信息 (PMI) 权重，生成图谱节点与边；
- `keyword_graph_build_compensate`: 补偿方法，重置并清理已计算的共现关系边；
- `keyword_graph_build_fallback`: 降级策略，跳过昂贵的全局 PMI 矩阵，仅保留一阶高频共现关系；
- `keyword_graph_build_metrics`: 统计网络节点数、边数及拓扑计算耗时；
- `keyword_graph_build_recall`: 图谱就绪回调，通知前端展示概念雷达网络。

### 2.4 思维导图提取方法组：`mindmap_generate`
- `mindmap_generate`: 主方法，基于目录树 AST 遍历及章节关键词聚类生成折叠导图树；
- `mindmap_generate_compensate`: 补偿方法，清除损坏或未完成的导图树缓存；
- `mindmap_generate_fallback`: 降级策略，当 AST 损坏时仅按一级标题抽取扁平目录树；
- `mindmap_generate_metrics`: 记录导图深度、节点总量与构建延时；
- `mindmap_generate_recall`: 导图构建完毕回调，驱动正文双向跳转联动初始化。

### 2.5 批注与边注管理方法组：`annotation_manage`
- `annotation_manage`: 主方法，执行高亮选区锚点计算、段落基线对齐持久化及 Markdown 导出；
- `annotation_manage_compensate`: 补偿方法，撤销错误的批注写入事务并还原版本号；
- `annotation_manage_fallback`: 降级策略，数据库锁定时暂存至内存本地队列并稍后重试持久化；
- `annotation_manage_metrics`: 记录批注保存耗时与批注总数；
- `annotation_manage_recall`: 边注保存回调，刷新桌面端 Margin 栏与移动端微标。

### 2.6 AI 伴读与认知模板方法组：`ai_companion_stream`
- `ai_companion_stream`: 主方法，装配 4 大认知模板上下文并发起流式交互；
- `ai_companion_stream_compensate`: 补偿方法，取消中断的请求并清理未完成会话片段；
- `ai_companion_stream_fallback`: 降级策略，当外部 API 超时或不可用时，降级输出本地预置的启发式思考引导卡片；
- `ai_companion_stream_metrics`: 记录首字延迟 (TTFT)、总耗时与 Token 开销；
- `ai_companion_stream_recall`: 伴读响应完毕回调，引导用户一键沉淀为正文边注。
