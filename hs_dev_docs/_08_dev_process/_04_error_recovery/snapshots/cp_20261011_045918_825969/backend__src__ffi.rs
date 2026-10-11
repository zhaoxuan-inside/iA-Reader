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
        let storage = SqliteStorage::init_db("ai_reader_data.db").expect("Failed to initialize SQLite storage");
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
            Ok(json!({
                "meta": meta,
                "sections": sections
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
        _ => Err(format!("Unknown action: {}", action)),
    }
}
