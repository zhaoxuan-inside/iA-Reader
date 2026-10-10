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
    pub parent_id: Option<i64>,
    pub start_page: i32,
    pub end_page: i32,
    pub content: Option<String>,
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
    pub style: String, // highlight | underline | margin_note
    pub note_text: Option<String>,
    pub anchor_json: String,
    pub ai_response: Option<String>,
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
