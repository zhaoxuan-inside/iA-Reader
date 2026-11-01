// backend/src/domain.rs
// AI Reader 领域模型定义 (DDD Domain Layer)

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookMeta {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub title: String,
    pub author: Option<String>,
    pub file_path: String,
    pub file_hash: String,
    pub format: String,
    pub total_pages: i32,
    pub read_progress: f64,
    pub last_read_at: Option<String>,
    /// 续读锚点：上次阅读停留的章节 id / 段落序号 / 段内字符偏移（FEAT-002 REQ-005）
    #[serde(default)]
    pub read_section_id: Option<i64>,
    #[serde(default)]
    pub read_paragraph_index: i32,
    #[serde(default)]
    pub read_char_offset: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookSection {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub section_index: i32,
    pub title: String,
    /// Markdown 标题层级（# =1 … ###### =6；无标题正文节 =1）
    #[serde(default = "default_section_level")]
    pub level: i32,
    pub parent_id: Option<i64>,
    pub start_page: i32,
    pub end_page: i32,
    pub content: Option<String>,
}

fn default_section_level() -> i32 {
    1
}

/// 正文段落（FEAT-002 三级结构：章节 → 段落 → 句子）。
/// 段落是阅读渲染与批注锚定的最小单元；char_offset 为全文绝对字符偏移。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParagraphNode {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub section_id: i64,
    pub paragraph_index: i32,
    pub text: String,
    pub page_number: i32,
    pub char_offset_start: i32,
    pub char_offset_end: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentenceNode {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub section_id: i64,
    pub sentence_index: i32,
    pub text: String,
    pub page_number: i32,
    pub char_offset_start: i32,
    pub char_offset_end: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeywordNode {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub word: String,
    pub level: String, // book | section | sentence
    pub tfidf_score: f64,
    pub textrank_score: f64,
    pub frequency: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeywordRelation {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub source_word_id: i64,
    pub target_word_id: i64,
    pub co_occurrence_count: i32,
    pub pmi_score: f64,
    pub weight: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MindmapNode {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub parent_id: Option<i64>,
    pub title: String,
    pub section_id: Option<i64>,
    pub level: i32,
    pub sort_order: i32,
    pub keywords_json: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Annotation {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub section_id: Option<i64>,
    pub color: String,
    /// highlight | halfHighlight | underline | wavy | strike | bold | italic | margin_note
    pub style: String,
    pub note_text: Option<String>,
    pub anchor_json: String,
    pub ai_response: Option<String>,
    /// manual（人工标注）| companion（AI 伴读沉淀边注）
    #[serde(default = "default_annotation_origin")]
    pub origin: String,
    /// 幂等归档键（FEAT-007 REQ-003）：AI 存边注重复提交时定位既有行而非重复插入
    #[serde(default)]
    pub idem_key: Option<String>,
}

fn default_annotation_origin() -> String {
    "manual".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiConversation {
    pub id: i64,
    pub created_at: String,
    pub updated_at: String,
    pub description: Option<String>,
    pub is_del: i32,
    pub version: i32,
    pub book_id: i64,
    pub section_id: Option<i64>,
    pub template_type: String, // general | logic | critical | term
    pub prompt: String,
    pub response: String,
    pub latency_ms: f64,
    /// 多轮追问线程 id：同 thread 的会话按 id 序还原完整上下文（FEAT-005 REQ-003）
    #[serde(default)]
    pub thread_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvokeMetrics {
    pub duration_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvokeEnvelope<T> {
    pub code: i32,
    pub message: String,
    pub data: Option<T>,
    pub metrics: Option<InvokeMetrics>,
}
