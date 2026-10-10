# AI Reader 跨语言 FFI 接口契约说明书 (Interface Design)

**文档编号**：IF-001  
**生命周期阶段**：阶段 3 - 详细规格设计  
**编写时间**：2026-10-10  
**状态**：APPROVED  

---

## 1. 跨语言 C-ABI 核心入口定义

Rust 暴露给 Flutter/Dart 的基础 C-ABI 入口：
```c
// 统一分发调用接口
char* ai_reader_invoke(const char* action, const char* payload);

// 释放由 Rust 分配给 Dart 的 UTF-8 字符串内存
void ai_reader_free_string(char* ptr);
```

---

## 2. 统一信封格式 (Invoke Envelope)

### 2.1 请求载荷 (Request)
- `action` (字符串枚举): 动作路由键
- `payload` (JSON 字符串): 业务参数

### 2.2 响应载荷 (Response)
```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "metrics": {
    "duration_ms": 15.2
  }
}
```
错误码规范：
- `0`: 成功 (`SUCCESS`)
- `40001`: 参数校验失败 (`INVALID_ARGUMENT`)
- `40401`: 资源未找到 (`NOT_FOUND`)
- `50001`: 内部计算或解析异常 (`INTERNAL_ERROR`)
- `50301`: 外部 AI 服务不可用已降级 (`AI_SERVICE_DEGRADED`)

---

## 3. 核心 Action 接口规格定义

### 3.1 `doc.parse` (文档解析与导入)
- **请求 Payload**:
  ```json
  { "file_path": "/path/to/book.epub" }
  ```
- **响应 Data**:
  ```json
  {
    "book_id": 1,
    "title": "深度学习导论",
    "author": "张三",
    "format": "epub",
    "total_pages": 320,
    "sections_count": 18
  }
  ```

### 3.2 `nlp.extract_keywords` (关键词打分与提取)
- **请求 Payload**:
  ```json
  { "book_id": 1, "top_n": 50 }
  ```
- **响应 Data**:
  ```json
  {
    "keywords": [
      { "id": 1, "word": "注意力机制", "level": "book", "tfidf_score": 0.85, "textrank_score": 0.92, "frequency": 45 },
      { "id": 2, "word": "残差网络", "level": "book", "tfidf_score": 0.78, "textrank_score": 0.88, "frequency": 38 }
    ]
  }
  ```

### 3.3 `nlp.build_graph` (概念共现网络拓扑计算)
- **请求 Payload**:
  ```json
  { "book_id": 1, "min_co_occurrence": 2 }
  ```
- **响应 Data**:
  ```json
  {
    "nodes": [ { "id": 1, "name": "注意力机制", "val": 45 } ],
    "links": [ { "source": 1, "target": 2, "weight": 0.65, "pmi": 2.4 } ]
  }
  ```

### 3.4 `mindmap.generate` (结构化思维导图提取)
- **请求 Payload**:
  ```json
  { "book_id": 1 }
  ```
- **响应 Data**:
  ```json
  {
    "root": {
      "id": 1,
      "title": "深度学习导论",
      "children": [
        { "id": 2, "title": "第一章 神经网络基础", "section_id": 1, "keywords": ["感知机", "反向传播"] }
      ]
    }
  }
  ```

### 3.5 `annotation.save` (保存文本高亮与边注)
- **请求 Payload**:
  ```json
  {
    "book_id": 1,
    "section_id": 1,
    "color": "#FFE066",
    "style": "margin_note",
    "note_text": "此处是Transformer核心公式",
    "anchor": {
      "page": 12,
      "char_offset_start": 450,
      "char_offset_end": 520,
      "selected_text": "Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V"
    }
  }
  ```
- **响应 Data**:
  ```json
  { "annotation_id": 1, "status": "saved" }
  ```

### 3.6 `ai.companion_ask` (认知伴读模板触发与追问)
- **请求 Payload**:
  ```json
  {
    "book_id": 1,
    "template_type": "logic",
    "selected_text": "在深度模型中，残差连接解决了梯度消失问题...",
    "prompt": "请用逻辑三段论分析作者的前提与推导"
  }
  ```
- **响应 Data**:
  ```json
  {
    "response": "【前提】随着网络深度增加，反向传播链式法则导致梯度指数级衰减...\n【推导】残差网络引入恒等映射（Identity Mapping）...\n【结论】梯度可跨层直接回传，从而打破网络退化瓶颈。",
    "latency_ms": 320.5
  }
  ```
