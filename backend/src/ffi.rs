// backend/src/ffi.rs
// C-ABI 跨语言 FFI 导出与请求分发网关

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::sync::{Mutex, OnceLock};
use std::time::Instant;
use serde_json::{json, Value};
use crate::service::ReaderService;
use crate::storage::SqliteStorage;

static SERVICE: OnceLock<Mutex<ReaderService>> = OnceLock::new();

// @PublicAPI
fn get_service() -> &'static Mutex<ReaderService> {
    SERVICE.get_or_init(|| {
        // ADR_005：集中存储初始化（目录/迁移/文件日志），db 落在 <base>/data/ai_reader.db
        let rt = crate::paths::runtime();
        let storage = SqliteStorage::init_db(&rt.db_path.to_string_lossy())
            .expect("Failed to initialize SQLite storage");
        Mutex::new(ReaderService::new(storage))
    })
}

#[no_mangle]
pub extern "C" fn ai_reader_invoke(action: *const c_char, payload: *const c_char) -> *mut c_char {
    let start = Instant::now();
    if action.is_null() || payload.is_null() {
        let err_json = json!({
            "code": 40001,
            "message": "Action or payload pointer is NULL",
            "data": null,
            "metrics": { "duration_ms": 0.0 }
        }).to_string();
        return CString::new(err_json).unwrap().into_raw();
    }

    let action_str = unsafe { CStr::from_ptr(action).to_string_lossy().to_string() };
    let payload_str = unsafe { CStr::from_ptr(payload).to_string_lossy().to_string() };

    let res = dispatch_invoke(&action_str, &payload_str);
    let duration_ms = start.elapsed().as_secs_f64() * 1000.0;

    let envelope = match res {
        Ok(data) => json!({
            "code": 0,
            "message": "success",
            "data": data,
            "metrics": { "duration_ms": duration_ms }
        }),
        Err(err_msg) => json!({
            "code": 50001,
            "message": err_msg,
            "data": null,
            "metrics": { "duration_ms": duration_ms }
        }),
    };

    CString::new(envelope.to_string()).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn ai_reader_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

pub fn dispatch_invoke(action: &str, payload: &str) -> Result<Value, String> {
    execute_action(action, payload)
}

pub fn execute_action(action: &str, payload: &str) -> Result<Value, String> {
    let service_guard = get_service().lock().unwrap();
    let val: Value = serde_json::from_str(payload).unwrap_or(json!({}));

    match action {
        "doc.parse" => {
            let file_path = val.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
            let meta = service_guard.doc_parse(file_path)?;
            Ok(serde_json::to_value(meta).map_err(|e| e.to_string())?)
        }
        "doc.list" => {
            let books = service_guard.storage.list_books().map_err(|e| e.to_string())?;
            Ok(serde_json::to_value(books).map_err(|e| e.to_string())?)
        }
        "doc.get" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let meta = service_guard.storage.get_book(book_id).map_err(|e| e.to_string())?;
            let sections = service_guard.storage.get_sections(book_id).map_err(|e| e.to_string())?;

            // FFI 契约（前端 _loadDocumentData / bridge mock）：sections[].paragraphs[]。
            // 引擎此前只回 section 行，正文从未进入前端——阅读区恒空白。
            // 段落优先取 sentence_node 切片；缺失时按空行切分 content 兜底（跳过 markdown 标题行）。
            let mut section_payloads = Vec::with_capacity(sections.len());
            for section in &sections {
                let sentences = service_guard
                    .storage
                    .get_sentences(section.id)
                    .unwrap_or_default();
                let paragraphs: Vec<Value> = if sentences.is_empty() {
                    split_content_paragraphs(section.id, section.content.as_deref().unwrap_or(""))
                } else {
                    sentences
                        .iter()
                        .map(|s| {
                            json!({
                                "id": format!("p{}", s.id),
                                "section_id": s.section_id,
                                "text": s.text,
                            })
                        })
                        .collect()
                };
                let mut sec_value =
                    serde_json::to_value(section).map_err(|e| e.to_string())?;
                if let Some(obj) = sec_value.as_object_mut() {
                    obj.insert("paragraphs".to_string(), Value::Array(paragraphs));
                }
                section_payloads.push(sec_value);
            }

            let title = meta.as_ref().map(|m| m.title.clone()).unwrap_or_default();
            Ok(json!({
                "book_id": book_id,
                "title": title,
                "meta": meta,
                "sections": section_payloads
            }))
        }
        "nlp.extract_keywords" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let top_n = val.get("top_n").and_then(|v| v.as_u64()).unwrap_or(30) as usize;
            let keywords = service_guard.nlp_keyword_extract(book_id, top_n)?;
            Ok(json!({ "keywords": keywords }))
        }
        "nlp.build_graph" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let min_co = val.get("min_co_occurrence").and_then(|v| v.as_i64()).unwrap_or(1) as i32;
            let relations = service_guard.keyword_graph_build(book_id, min_co)?;
            let keywords = service_guard.storage.get_keywords(book_id).unwrap_or_default();
            Ok(json!({
                "nodes": keywords,
                "links": relations
            }))
        }
        "mindmap.generate" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let nodes = service_guard.mindmap_generate(book_id)?;
            Ok(json!({ "nodes": nodes }))
        }
        "annotation.save" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let section_id = val.get("section_id").and_then(|v| v.as_i64());
            let color = val.get("color").and_then(|v| v.as_str()).unwrap_or("#FFE066").to_string();
            let style = val.get("style").and_then(|v| v.as_str()).unwrap_or("highlight").to_string();
            let note_text = val.get("note_text").and_then(|v| v.as_str()).map(|s| s.to_string());
            let anchor_json = val.get("anchor").map(|v| v.to_string()).unwrap_or_else(|| "{}".to_string());
            let ai_response = val.get("ai_response").and_then(|v| v.as_str()).map(|s| s.to_string());

            let annot = crate::domain::Annotation {
                id: 0,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                section_id,
                color,
                style,
                note_text,
                anchor_json,
                ai_response,
            };
            let id = service_guard.annotation_manage(&annot)?;
            Ok(json!({ "annotation_id": id, "status": "saved" }))
        }
        "annotation.list" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let list = service_guard.storage.get_annotations(book_id).map_err(|e| e.to_string())?;
            Ok(json!({ "annotations": list }))
        }
        "ai.companion_ask" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let template_type = val.get("template_type").and_then(|v| v.as_str()).unwrap_or("general");
            let selected_text = val.get("selected_text").and_then(|v| v.as_str()).unwrap_or("");
            let prompt = val.get("prompt").and_then(|v| v.as_str()).unwrap_or("");
            let response = service_guard.ai_companion_stream(book_id, template_type, selected_text, prompt)?;
            Ok(json!({
                "response": response,
                "template_type": template_type
            }))
        }
        "config.get" => {
            let cfg = crate::llm::LlmConfig::load();
            let rt = crate::paths::runtime();
            Ok(json!({
                "config": cfg,
                "config_path": crate::llm::user_config_path().to_string_lossy(),
                "paths": {
                    "base": rt.base.to_string_lossy(),
                    "data": rt.data_dir.to_string_lossy(),
                    "logs": rt.log_dir.to_string_lossy(),
                    "books": rt.books_dir.to_string_lossy(),
                    "config": rt.llm_config_path.to_string_lossy(),
                    "db": rt.db_path.to_string_lossy(),
                },
            }))
        }
        "config.save" => {
            // payload.config 允许部分字段：键级 merge 到当前生效配置后整体校验并覆写
            let base = crate::llm::LlmConfig::load();
            let cfg = crate::llm::overlay_config(&base, val.get("config"))?;
            crate::llm::save_user_config(&crate::llm::user_config_path(), &cfg)?;
            Ok(json!({
                "saved": true,
                "config": cfg,
                "config_path": crate::llm::user_config_path().to_string_lossy(),
            }))
        }
        "config.test" => {
            // payload.config 可携带未保存的表单值先行验证；单次调用不重试
            let base = crate::llm::LlmConfig::load();
            let cfg = crate::llm::overlay_config(&base, val.get("config"))?;
            let latency_ms = crate::llm::test_llm_connection(&crate::llm::UreqLlmClient, &cfg)?;
            Ok(json!({ "ok": true, "latency_ms": latency_ms as f64 }))
        }
        _ => Err(format!("Unknown action: {}", action)),
    }
}

/// 将章节 markdown content 按空行切分为正文段落，跳过纯标题块。
/// 仅作为 sentence_node 切片缺失时的兜底，保证阅读区正文不因历史数据缺句而空白。
fn split_content_paragraphs(section_id: i64, content: &str) -> Vec<Value> {
    let mut paragraphs = Vec::new();
    for (idx, block) in content.split("\n\n").enumerate() {
        let text = block.trim().to_string();
        if text.is_empty() || text.lines().all(|l| l.trim_start().starts_with('#')) {
            continue;
        }
        paragraphs.push(json!({
            "id": format!("p{}_{}", section_id, idx + 1),
            "section_id": section_id,
            "text": text,
        }));
    }
    paragraphs
}
