// backend/src/ffi.rs
// C-ABI 跨语言 FFI 导出与请求分发网关

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::sync::OnceLock;
use std::time::Instant;
use serde_json::{json, Value};
use crate::service::ReaderService;
use crate::storage::SqliteStorage;

// 引擎全局单例：无外层 Mutex 直接共享（并发安全由 storage 内部 Arc<Mutex<Connection>>
// 保证；ReaderService: Send+Sync）——此前整表锁串行化全部 action，秒级 book.parse
// 会阻塞伴读轮询等其余调用。初始化失败以 Err 落入单例并透传错误信封，
// 禁止 expect panic 直接击穿宿主进程。
static SERVICE: OnceLock<Result<ReaderService, String>> = OnceLock::new();

fn get_service() -> Result<&'static ReaderService, String> {
    SERVICE
        .get_or_init(|| {
            // ADR_005：集中存储初始化（目录/迁移/文件日志），db 落在 <base>/data/ai_reader.db
            let rt = crate::paths::runtime();
            match SqliteStorage::init_db(&rt.db_path.to_string_lossy()) {
                Ok(storage) => Ok(ReaderService::new(storage)),
                Err(e) => Err(format!("SQLite storage init failed: {}", e)),
            }
        })
        .as_ref()
        .map_err(|e| e.clone())
}

/// clippy::not_unsafe_ptr_arg_deref：空指针在解引用前已显式检查并返回错误信封，
/// 声明为 safe extern 是宿主（Dart FFI）契约要求
#[no_mangle]
#[allow(clippy::not_unsafe_ptr_arg_deref)]
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
#[allow(clippy::not_unsafe_ptr_arg_deref)]
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

/// 流式伴读三通道（task_17 D3）：免锁执行。
fn execute_companion_action(action: &str, val: &Value) -> Result<Value, String> {
    if action == "ai.companion_poll" {
        let request_id = val
            .get("request_id")
            .and_then(|v| v.as_str())
            .ok_or("ai.companion_poll requires request_id")?;
        let state = crate::service::companion_poll(request_id)
            .ok_or_else(|| format!("unknown companion stream: {}", request_id))?;
        // TTFT（FEAT-005 REQ-002）：首 delta 到达 - 启动时刻；未收到 delta 时为 null
        let ttft_ms = state
            .first_delta_at_ms
            .filter(|t| *t >= state.started_at_ms)
            .map(|t| (t - state.started_at_ms) as f64);
        return Ok(json!({
            "partial": state.partial,
            "done": state.done,
            "offline": state.offline,
            "ttft_ms": ttft_ms,
        }));
    }

    let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
    let template_type = val.get("template_type").and_then(|v| v.as_str()).unwrap_or("general");
    let selected_text = val.get("selected_text").and_then(|v| v.as_str()).unwrap_or("");
    let prompt = val.get("prompt").and_then(|v| v.as_str()).unwrap_or("");
    // 多轮追问线程：前端传入既有 thread_id 续上下文；缺省生成新线程
    let thread_id = match val.get("thread_id").and_then(|v| v.as_str()) {
        Some(tid) if !tid.trim().is_empty() => tid.trim().to_string(),
        _ => format!(
            "ct_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos()
        ),
    };

    let storage = get_service()?.storage.clone();
    let config = crate::llm::LlmConfig::load();
    let request_id = crate::service::companion_start(crate::service::CompanionStartParams {
        client: Box::new(crate::llm::UreqLlmClient),
        storage,
        config,
        book_id,
        template_type: template_type.to_string(),
        selected_text: selected_text.to_string(),
        prompt: prompt.to_string(),
        thread_id: Some(thread_id.clone()),
    });

    if action == "ai.companion_start" {
        return Ok(json!({ "request_id": request_id, "thread_id": thread_id }));
    }

    // ai.companion_ask：轮询 join 至终态（契约兼容：response/template_type 不变）。
    // 先 poll 再退避：此前首轮先睡 30ms，离线卡片这类即终场景被无谓拖慢一个轮询周期
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(180);
    let mut response = String::new();
    let mut offline = false;
    // 自适应退避轮询：2ms 起步倍增至 30ms 封顶——离线卡片这类即终场景
    // 毫秒级收敛（SLA <10ms），长生成场景退避到与流式节奏匹配的低占用
    let mut backoff_ms: u64 = 2;
    while let Some(state) = crate::service::companion_poll(&request_id) {
        response = state.partial.clone();
        offline = state.offline;
        if state.done {
            break;
        }
        if std::time::Instant::now() > deadline {
            crate::log_warn!("[TIMEOUT] companion_ask join exceeded 180s, return partial");
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(backoff_ms));
        backoff_ms = (backoff_ms * 2).min(30);
    }
    let _ = offline;
    Ok(json!({
        "response": response,
        "template_type": template_type,
        "request_id": request_id,
    }))
}

pub fn execute_action(action: &str, payload: &str) -> Result<Value, String> {
    // 空/空白 payload 视为 {}（CLI 便捷调用）；非空但畸形必须显式报错——
    // 此前静默当 {} 会把调用方的拼写/编码错误掩盖成"成功空结果"
    let trimmed = payload.trim();
    let val: Value = if trimmed.is_empty() {
        json!({})
    } else {
        serde_json::from_str(trimmed).map_err(|e| format!("payload JSON 无效: {}", e))?
    };

    // 流式伴读三通道（task_17 D3）：LLM 调用全程不占全局单例——
    // companion_start 派生线程执行，companion_poll 只读注册表；
    // companion_ask 以 start+轮询 join 保持旧契约。
    if action == "ai.companion_start" || action == "ai.companion_poll" || action == "ai.companion_ask" {
        return execute_companion_action(action, &val);
    }

    let service = get_service()?;

    match action {
        "book.parse" => {
            let file_path = val.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
            let outcome = service.doc_parse(file_path)?;
            let mut meta_value = serde_json::to_value(&outcome.meta).map_err(|e| e.to_string())?;
            if let Some(obj) = meta_value.as_object_mut() {
                // 幂等定位契约：duplicate=true 时 data.id 即既有书目，前端直接定位打开
                obj.insert("duplicate".to_string(), json!(outcome.duplicate));
            }
            Ok(meta_value)
        }
        "book.list" => {
            let books = service.storage.list_books().map_err(|e| e.to_string())?;
            // FFI 契约（前端 LibraryScreen._loadBooks）：data 必须是 {books:[...]} 信封 Map——
            // 裸数组会令 Dart 侧 InvokeEnvelope 解析抛错并静默回退 mock 假书单。
            let mut payload = Vec::with_capacity(books.len());
            for b in &books {
                let mut v = serde_json::to_value(b).map_err(|e| e.to_string())?;
                if let Some(obj) = v.as_object_mut() {
                    let count = service.storage.count_sections(b.id).unwrap_or(0);
                    obj.insert("sections_count".to_string(), json!(count));
                }
                payload.push(v);
            }
            Ok(json!({ "books": payload }))
        }
        "book.deleted" => {
            // FEAT-001 书库管理（book.deleted）：删除书籍并清理批注/伴读会话/章节句子等派生数据
            let book_id = val
                .get("book_id")
                .and_then(|v| v.as_i64())
                .ok_or("book.deleted requires book_id")?;
            let deleted = service
                .storage
                .delete_book_full(book_id)
                .map_err(|e| e.to_string())?;
            if !deleted {
                return Err(format!("book not found: {}", book_id));
            }
            Ok(json!({ "status": "deleted", "book_id": book_id }))
        }
        "book.get" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            // 打开即阅读行为：刷新 last_read_at（书库"最近阅读"排序依据）
            let _ = service.storage.touch_last_read(book_id);
            let meta = service.storage.get_book(book_id).map_err(|e| e.to_string())?;
            let sections = service.storage.get_sections(book_id).map_err(|e| e.to_string())?;

            // FFI 契约（前端 _loadDocumentData / bridge mock）：sections[].paragraphs[]。
            // 段落取 paragraph_node（FEAT-002 三级结构）；
            // 缺失时按空行切分 content 兜底（跳过 markdown 标题行），老库数据不至于空白。
            let mut section_payloads = Vec::with_capacity(sections.len());
            for section in &sections {
                let paragraphs: Vec<Value> = match service.storage.get_paragraphs(section.id) {
                    Ok(rows) if !rows.is_empty() => rows
                        .iter()
                        .map(|p| {
                            json!({
                                "id": format!("p{}", p.id),
                                "section_id": p.section_id,
                                "text": p.text,
                                "index": p.paragraph_index,
                                "char_offset_start": p.char_offset_start,
                                "char_offset_end": p.char_offset_end,
                            })
                        })
                        .collect(),
                    _ => split_content_paragraphs(section.id, section.content.as_deref().unwrap_or("")),
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
        // 续读进度（FEAT-002 REQ-005）：锚点落库 + 读取，书架恢复入口依赖 meta.read_*
        "progress.save" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let section_id = val.get("section_id").and_then(|v| v.as_i64());
            let paragraph_index = val.get("paragraph_index").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let char_offset = val.get("char_offset").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let progress = val.get("progress").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let ok = service
                .storage
                .save_read_progress(book_id, section_id, paragraph_index, char_offset, progress)
                .map_err(|e| e.to_string())?;
            if !ok {
                return Err(format!("book not found: {}", book_id));
            }
            Ok(json!({ "status": "saved", "book_id": book_id }))
        }
        "progress.get" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let meta = service
                .storage
                .get_book(book_id)
                .map_err(|e| e.to_string())?
                .ok_or_else(|| format!("book not found: {}", book_id))?;
            Ok(json!({
                "book_id": book_id,
                "read_section_id": meta.read_section_id,
                "read_paragraph_index": meta.read_paragraph_index,
                "read_char_offset": meta.read_char_offset,
                "read_progress": meta.read_progress,
            }))
        }
        // 兼容双名：前端唯一下单名 nlp.keyword_extract；引擎规范名 nlp.extract_keywords
        "nlp.keyword_extract" | "nlp.extract_keywords" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let top_n = val.get("top_n").and_then(|v| v.as_u64()).unwrap_or(30) as usize;
            let keywords = service.nlp_keyword_extract(book_id, top_n)?;
            // FFI 契约（前端 KeywordTagItem / 词云字号映射）：word/score/count
            let items: Vec<Value> = keywords
                .iter()
                .map(|k| json!({ "word": k.word, "score": k.tfidf_score, "count": k.frequency }))
                .collect();
            Ok(json!({ "keywords": items }))
        }
        "nlp.build_graph" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let min_co = val.get("min_co_occurrence").and_then(|v| v.as_i64()).unwrap_or(1) as i32;
            let relations = service.keyword_graph_build(book_id, min_co)?;
            let keywords = service.storage.get_keywords(book_id).unwrap_or_default();
            Ok(json!({
                "nodes": keywords,
                "links": relations
            }))
        }
        "mindmap.generate" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let nodes = service.mindmap_generate(book_id)?;
            // FFI 契约（前端 MindmapNodeItem）：label/depth（引擎内为 title/level）
            let items: Vec<Value> = nodes
                .iter()
                .map(|n| {
                    json!({
                        "id": n.id,
                        "label": n.title,
                        "depth": n.level,
                        "parent_id": n.parent_id,
                        "section_id": n.section_id,
                    })
                })
                .collect();
            Ok(json!({ "nodes": items }))
        }
        "annotation.save" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let section_id = val.get("section_id").and_then(|v| v.as_i64());
            let color = val.get("color").and_then(|v| v.as_str()).unwrap_or("#FFE066").to_string();
            let style = val.get("style").and_then(|v| v.as_str()).unwrap_or("highlight").to_string();
            // 样式白名单校验（FEAT-007）：7 种标注样式 + 边注；此前引擎对 style 零校验，
            // 拼写错误静默入库后渲染层无法匹配
            const VALID_STYLES: [&str; 8] = [
                "highlight", "half_highlight", "underline", "wavy", "strike", "bold", "italic", "margin_note",
            ];
            if !VALID_STYLES.contains(&style.as_str()) {
                return Err(format!(
                    "annotation style 非法: {}（可选: {}）",
                    style,
                    VALID_STYLES.join(", ")
                ));
            }
            let note_text = val.get("note_text").and_then(|v| v.as_str()).map(|s| s.to_string());
            let anchor_json = val.get("anchor").map(|v| v.to_string()).unwrap_or_else(|| "{}".to_string());
            let ai_response = val.get("ai_response").and_then(|v| v.as_str()).map(|s| s.to_string());
            // origin（manual|companion）+ idem_key（AI 存边注幂等归档）
            let origin = val.get("origin").and_then(|v| v.as_str()).unwrap_or("manual").to_string();
            if origin != "manual" && origin != "companion" {
                return Err(format!("annotation origin 非法: {}（可选: manual, companion）", origin));
            }
            let idem_key = val
                .get("idem_key")
                .and_then(|v| v.as_str())
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty());

            let annotation = crate::domain::Annotation {
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
                origin,
                idem_key,
            };
            let id = service.annotation_manage(&annotation)?;
            // 幂等命中时 status=existed：前端可区分新归档与重复归档
            let existed = annotation
                .idem_key
                .as_deref()
                .and_then(|k| service.storage.find_annotation_id_by_idem(book_id, k).ok())
                .flatten()
                .is_some();
            Ok(json!({ "annotation_id": id, "status": if existed { "existed" } else { "saved" } }))
        }
        "annotation.list" => {
            let book_id = val.get("book_id").and_then(|v| v.as_i64()).unwrap_or(0);
            let list = service.storage.get_annotations(book_id).map_err(|e| e.to_string())?;
            Ok(json!({ "annotations": list }))
        }
        "annotation.deleted" => {
            let annotation_id = val
                .get("annotation_id")
                .and_then(|v| v.as_i64())
                .ok_or("annotation.deleted requires annotation_id")?;
            service
                .storage
                .delete_annotation(annotation_id)
                .map_err(|e| e.to_string())?;
            Ok(json!({ "status": "deleted", "annotation_id": annotation_id }))
        }
        "annotation.updated" => {
            let annotation_id = val
                .get("annotation_id")
                .and_then(|v| v.as_i64())
                .ok_or("annotation.updated requires annotation_id")?;
            let note_text = val.get("note_text").and_then(|v| v.as_str());
            let color = val.get("color").and_then(|v| v.as_str());
            let style = val.get("style").and_then(|v| v.as_str());
            let changed = service
                .storage
                .update_annotation(annotation_id, note_text, color, style)
                .map_err(|e| e.to_string())?;
            Ok(json!({ "status": if changed { "updated" } else { "not_found" }, "annotation_id": annotation_id }))
        }
        // ai.companion_ask 在 execute_action 顶部已拦截走流式管线，此臂不可达，已移除
        "settings.get" => {
            // 应用配置读取（主题模式/上次书目等 GUI 偏好，集中存储于 app_settings 表）
            let keys: Vec<String> = val
                .get("keys")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|k| k.as_str().map(String::from)).collect())
                .unwrap_or_default();
            let settings = service
                .storage
                .get_app_settings(&keys)
                .map_err(|e| e.to_string())?;
            Ok(json!({ "settings": settings }))
        }
        "settings.save" => {
            let mut settings = std::collections::HashMap::new();
            if let Some(map) = val.get("settings").and_then(|v| v.as_object()) {
                for (k, v) in map {
                    let value = match v {
                        Value::String(s) => s.clone(),
                        other => other.to_string(),
                    };
                    settings.insert(k.clone(), value);
                }
            }
            service
                .storage
                .save_app_settings(&settings)
                .map_err(|e| e.to_string())?;
            Ok(json!({ "status": "saved", "count": settings.len() }))
        }
        "config.get" => {
            let cfg = crate::llm::LlmConfig::load();
            let rt = crate::paths::runtime();
            // PRD NFR「密钥不回显明文」：api_key 以掩码返回并附尾号提示；
            // 真实密钥仅存本机配置文件，不进入任何返回通道
            let configured = !cfg.api_key.trim().is_empty();
            let mut cfg_json = serde_json::to_value(&cfg).map_err(|e| e.to_string())?;
            if let Some(obj) = cfg_json.as_object_mut() {
                obj.insert("api_key".to_string(), json!(if configured { crate::llm::API_KEY_MASK } else { "" }));
                obj.insert("api_key_configured".to_string(), json!(configured));
                obj.insert("api_key_tail".to_string(), json!(crate::llm::api_key_tail(&cfg)));
            }
            Ok(json!({
                "config": cfg_json,
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
            // 返回值同样掩码（与 config.get 同口径，密钥不出引擎）
            let configured = !cfg.api_key.trim().is_empty();
            let mut cfg_json = serde_json::to_value(&cfg).map_err(|e| e.to_string())?;
            if let Some(obj) = cfg_json.as_object_mut() {
                obj.insert("api_key".to_string(), json!(if configured { crate::llm::API_KEY_MASK } else { "" }));
                obj.insert("api_key_configured".to_string(), json!(configured));
                obj.insert("api_key_tail".to_string(), json!(crate::llm::api_key_tail(&cfg)));
            }
            Ok(json!({
                "saved": true,
                "config": cfg_json,
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
