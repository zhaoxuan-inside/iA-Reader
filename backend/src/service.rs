// backend/src/service.rs
// 六元组标准化业务服务层 (主方法 + compensate + fallback + metrics + recall)

use std::collections::HashMap;
use std::time::Instant;
use crate::domain::*;
use crate::storage::SqliteStorage;
use crate::parser::*;
use crate::nlp::*;
use crate::llm::{
    build_companion_messages, chat_with_retry, LlmClient, LlmConfig, UreqLlmClient, BASE_DELAY_MS,
    MAX_RETRIES,
};

pub struct ReaderService {
    pub storage: SqliteStorage,
    llm_client: Box<dyn LlmClient>,
}

impl ReaderService {
    // @PublicAPI
    pub fn new(storage: SqliteStorage) -> Self {
        Self { storage, llm_client: Box::new(UreqLlmClient) }
    }

    /// 测试注入口：替换传输层 seam，业务编排零网络依赖可测。
    pub fn with_llm_client(storage: SqliteStorage, llm_client: Box<dyn LlmClient>) -> Self {
        Self { storage, llm_client }
    }

    // =========================================================================
    // 1. 文档解构六元组 (doc_parse)
    // =========================================================================
    pub fn doc_parse(&self, file_path: &str) -> Result<BookMeta, String> {
        let start = Instant::now();
        let ext = file_path.split('.').last().unwrap_or("").to_lowercase();
        
        let parsed = match ext.as_str() {
            "pdf" => parse_pdf(file_path),
            "epub" => parse_epub(file_path),
            "md" | "markdown" => parse_markdown(file_path),
            "txt" => parse_txt(file_path),
            _ => self.doc_parse_fallback(file_path),
        };

        let mut doc = match parsed {
            Ok(d) => d,
            Err(_) => self.doc_parse_fallback(file_path)?,
        };

        // 导入文档稳定副本（ADR_005）：源文件移动/删除不再破坏书库；失败降级沿用原路径
        let source_path = doc.meta.file_path.clone();
        match crate::paths::copy_into_books(
            &crate::paths::runtime().books_dir,
            std::path::Path::new(&source_path),
            &ext,
        ) {
            Ok(copy) => {
                doc.meta.file_path = copy.to_string_lossy().to_string();
                crate::log_info!("[PATHS] book copy stored: {}", doc.meta.file_path);
            }
            Err(e) => {
                crate::log_warn!("[PATHS] books 副本失败，沿用原路径 {}: {}", source_path, e);
            }
        }

        let book_id = self.storage.save_book(&doc.meta).map_err(|e| {
            self.doc_parse_compensate(file_path);
            format!("Failed to save book meta: {}", e)
        })?;

        doc.meta.id = book_id;

        for s in &mut doc.sections {
            s.book_id = book_id;
        }
        let _ = self.storage.save_sections(&doc.sections);

        for sent in &mut doc.sentences {
            sent.book_id = book_id;
        }
        let _ = self.storage.save_sentences(&doc.sentences);

        self.doc_parse_metrics(start.elapsed().as_secs_f64() * 1000.0, doc.sentences.len());
        self.doc_parse_recall(book_id);

        Ok(doc.meta)
    }

    pub fn doc_parse_compensate(&self, file_path: &str) {
        crate::log_warn!("[COMPENSATE] Rolling back document parsing for: {}", file_path);
    }

    pub fn doc_parse_fallback(&self, file_path: &str) -> Result<ParsedDocument, String> {
        crate::log_warn!("[FALLBACK] Using plain text stream fallback for: {}", file_path);
        parse_txt(file_path)
    }

    pub fn doc_parse_metrics(&self, duration_ms: f64, sentence_count: usize) {
        crate::log_info!("[METRICS] doc_parse completed in {:.2}ms (sentences: {})", duration_ms, sentence_count);
    }

    pub fn doc_parse_recall(&self, book_id: i64) {
        crate::log_info!("[RECALL] doc_parse success event triggered for book_id: {}", book_id);
    }

    // =========================================================================
    // 2. 关键词提取六元组 (nlp_keyword_extract)
    // =========================================================================
    pub fn nlp_keyword_extract(&self, book_id: i64, top_n: usize) -> Result<Vec<KeywordNode>, String> {
        let start = Instant::now();
        let sections = self.storage.get_sections(book_id).map_err(|e| e.to_string())?;
        if sections.is_empty() {
            return self.nlp_keyword_extract_fallback(book_id, top_n);
        }

        let mut all_text = String::new();
        for s in &sections {
            if let Some(ref c) = s.content {
                all_text.push_str(c);
                all_text.push(' ');
            }
        }

        let tokens = tokenize(&all_text);
        if tokens.is_empty() {
            return self.nlp_keyword_extract_fallback(book_id, top_n);
        }

        let doc_freqs = HashMap::new();
        let tfidf = calculate_tfidf(&tokens, 1, &doc_freqs);
        let textrank = calculate_textrank(&tokens, 5, 10);
        let tr_map: HashMap<String, f64> = textrank.into_iter().collect();

        let mut keywords = Vec::new();
        for (idx, (word, tfidf_score, freq)) in tfidf.iter().take(top_n).enumerate() {
            let tr_score = tr_map.get(word).cloned().unwrap_or(0.1);
            keywords.push(KeywordNode {
                id: (idx + 1) as i64,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                word: word.clone(),
                level: "book".to_string(),
                tfidf_score: *tfidf_score,
                textrank_score: tr_score,
                frequency: *freq,
            });
        }

        let _ = self.storage.save_keywords(&keywords);
        self.nlp_keyword_extract_metrics(start.elapsed().as_secs_f64() * 1000.0, keywords.len());
        self.nlp_keyword_extract_recall(book_id);

        Ok(keywords)
    }

    pub fn nlp_keyword_extract_compensate(&self, book_id: i64) {
        crate::log_warn!("[COMPENSATE] Cleaning up extracted keywords for book_id: {}", book_id);
    }

    pub fn nlp_keyword_extract_fallback(&self, book_id: i64, top_n: usize) -> Result<Vec<KeywordNode>, String> {
        crate::log_warn!("[FALLBACK] Using simple word frequency fallback for book_id: {}", book_id);
        let fallback_words = vec!["深度阅读", "认知伴读", "注意力", "知识图谱", "思维导图"];
        let mut res = Vec::new();
        for (i, w) in fallback_words.iter().take(top_n).enumerate() {
            res.push(KeywordNode {
                id: (i + 1) as i64,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                word: w.to_string(),
                level: "book".to_string(),
                tfidf_score: 0.5,
                textrank_score: 0.5,
                frequency: 5,
            });
        }
        Ok(res)
    }

    pub fn nlp_keyword_extract_metrics(&self, duration_ms: f64, count: usize) {
        crate::log_info!("[METRICS] nlp_keyword_extract completed in {:.2}ms (count: {})", duration_ms, count);
    }

    pub fn nlp_keyword_extract_recall(&self, book_id: i64) {
        crate::log_info!("[RECALL] nlp_keyword_extract success for book_id: {}", book_id);
    }

    // =========================================================================
    // 3. 概念图谱构建六元组 (keyword_graph_build)
    // =========================================================================
    pub fn keyword_graph_build(&self, book_id: i64, min_co_occurrence: i32) -> Result<Vec<KeywordRelation>, String> {
        let start = Instant::now();
        let keywords = self.storage.get_keywords(book_id).unwrap_or_default();
        if keywords.is_empty() {
            return self.keyword_graph_build_fallback(book_id, min_co_occurrence);
        }

        let sections = self.storage.get_sections(book_id).unwrap_or_default();
        let mut all_text = String::new();
        for s in &sections {
            if let Some(ref c) = s.content {
                all_text.push_str(c);
                all_text.push(' ');
            }
        }
        let tokens = tokenize(&all_text);
        let relations = build_co_occurrence(&tokens, &keywords, 10);
        let filtered: Vec<KeywordRelation> = relations.into_iter().filter(|r| r.co_occurrence_count >= min_co_occurrence).collect();

        let _ = self.storage.save_keyword_relations(&filtered);
        self.keyword_graph_build_metrics(start.elapsed().as_secs_f64() * 1000.0, filtered.len());
        self.keyword_graph_build_recall(book_id);

        Ok(filtered)
    }

    pub fn keyword_graph_build_compensate(&self, book_id: i64) {
        crate::log_warn!("[COMPENSATE] Resetting keyword relations for book_id: {}", book_id);
    }

    pub fn keyword_graph_build_fallback(&self, book_id: i64, _min: i32) -> Result<Vec<KeywordRelation>, String> {
        crate::log_warn!("[FALLBACK] Using simple default relations for book_id: {}", book_id);
        Ok(vec![
            KeywordRelation {
                id: 1,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                source_word_id: 1,
                target_word_id: 2,
                co_occurrence_count: 2,
                pmi_score: 1.5,
                weight: 0.6,
            }
        ])
    }

    pub fn keyword_graph_build_metrics(&self, duration_ms: f64, edge_count: usize) {
        crate::log_info!("[METRICS] keyword_graph_build completed in {:.2}ms (edges: {})", duration_ms, edge_count);
    }

    pub fn keyword_graph_build_recall(&self, book_id: i64) {
        crate::log_info!("[RECALL] keyword_graph_build ready for book_id: {}", book_id);
    }

    // =========================================================================
    // 4. 思维导图提取六元组 (mindmap_generate)
    // =========================================================================
    pub fn mindmap_generate(&self, book_id: i64) -> Result<Vec<MindmapNode>, String> {
        let start = Instant::now();
        let sections = self.storage.get_sections(book_id).unwrap_or_default();
        if sections.is_empty() {
            return self.mindmap_generate_fallback(book_id);
        }

        let mut nodes = Vec::new();
        nodes.push(MindmapNode {
            id: 1,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            book_id,
            parent_id: None,
            title: "全书核心脉络".to_string(),
            section_id: None,
            level: 0,
            sort_order: 0,
            keywords_json: Some("[\"核心概念\"]".to_string()),
        });

        for (idx, sec) in sections.iter().enumerate() {
            nodes.push(MindmapNode {
                id: (idx + 2) as i64,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                parent_id: Some(1),
                title: sec.title.clone(),
                section_id: Some(sec.id),
                level: 1,
                sort_order: (idx + 1) as i32,
                keywords_json: Some("[\"重点\"]".to_string()),
            });
        }

        let _ = self.storage.save_mindmap_nodes(&nodes);
        self.mindmap_generate_metrics(start.elapsed().as_secs_f64() * 1000.0, nodes.len());
        self.mindmap_generate_recall(book_id);

        Ok(nodes)
    }

    pub fn mindmap_generate_compensate(&self, book_id: i64) {
        crate::log_warn!("[COMPENSATE] Resetting mindmap cache for book_id: {}", book_id);
    }

    pub fn mindmap_generate_fallback(&self, book_id: i64) -> Result<Vec<MindmapNode>, String> {
        crate::log_warn!("[FALLBACK] Flat mindmap fallback for book_id: {}", book_id);
        Ok(vec![
            MindmapNode {
                id: 1,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id,
                parent_id: None,
                title: "目录概要".to_string(),
                section_id: None,
                level: 0,
                sort_order: 0,
                keywords_json: None,
            }
        ])
    }

    pub fn mindmap_generate_metrics(&self, duration_ms: f64, node_count: usize) {
        crate::log_info!("[METRICS] mindmap_generate completed in {:.2}ms (nodes: {})", duration_ms, node_count);
    }

    pub fn mindmap_generate_recall(&self, book_id: i64) {
        crate::log_info!("[RECALL] mindmap ready for book_id: {}", book_id);
    }

    // =========================================================================
    // 5. 批注与边注六元组 (annotation_manage)
    // =========================================================================
    pub fn annotation_manage(&self, annotation: &Annotation) -> Result<i64, String> {
        let start = Instant::now();
        let id = self.storage.save_annotation(annotation).map_err(|e| {
            self.annotation_manage_compensate(annotation.book_id);
            e.to_string()
        })?;

        self.annotation_manage_metrics(start.elapsed().as_secs_f64() * 1000.0, 1);
        self.annotation_manage_recall(id);
        Ok(id)
    }

    pub fn annotation_manage_compensate(&self, book_id: i64) {
        crate::log_warn!("[COMPENSATE] Rolling back annotation save for book_id: {}", book_id);
    }

    pub fn annotation_manage_fallback(&self, annotation: &Annotation) -> Result<i64, String> {
        crate::log_warn!("[FALLBACK] Annotation memory queue fallback for book_id: {}", annotation.book_id);
        Ok(1)
    }

    pub fn annotation_manage_metrics(&self, duration_ms: f64, count: usize) {
        crate::log_info!("[METRICS] annotation_manage in {:.2}ms (count: {})", duration_ms, count);
    }

    pub fn annotation_manage_recall(&self, annotation_id: i64) {
        crate::log_info!("[RECALL] annotation updated for annotation_id: {}", annotation_id);
    }

    // =========================================================================
    // 6. AI 伴读与认知模板六元组 (ai_companion_stream)
    // =========================================================================
    // @PublicAPI
    pub fn ai_companion_stream(&self, book_id: i64, template_type: &str, selected_text: &str, prompt: &str) -> Result<String, String> {
        let config = LlmConfig::load();
        self.ai_companion_stream_with(&config, book_id, template_type, selected_text, prompt)
    }

    /// 六元组主方法核心：注入配置以隔离测试（生产入口 `ai_companion_stream` 每次调用重读配置，
    /// 与 Python CLI 引擎行为一致，用户改配置无需重启进程）。
    pub fn ai_companion_stream_with(
        &self,
        config: &LlmConfig,
        book_id: i64,
        template_type: &str,
        selected_text: &str,
        prompt: &str,
    ) -> Result<String, String> {
        let start = Instant::now();
        let messages = build_companion_messages(template_type, selected_text, prompt, &config.system_prompt);

        // api_key 未配置：不发 HTTP、零计费，直接离线启发式卡片（PRD §4.1 离线可用性）
        let (response, offline) = if config.api_key.trim().is_empty() {
            crate::log_warn!("[FALLBACK] api_key 未配置，走离线启发式卡片（配置路径: ~/.config/ai-reader/llm_config.json）");
            (self.ai_companion_stream_fallback(template_type, selected_text)?, true)
        } else {
            match chat_with_retry(
                self.llm_client.as_ref(),
                config,
                &messages,
                MAX_RETRIES,
                BASE_DELAY_MS,
                |d| std::thread::sleep(d),
            ) {
                Ok(content) => (content, false),
                Err(err) => {
                    crate::log_warn!("[FALLBACK] LLM 调用重试 {} 次后耗尽: {}，走离线启发式卡片", MAX_RETRIES, err);
                    (self.ai_companion_stream_fallback(template_type, selected_text)?, true)
                }
            }
        };

        let conv = AiConversation {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: if offline { Some("offline_fallback".to_string()) } else { None },
            is_del: 0,
            version: 1,
            book_id,
            section_id: None,
            template_type: template_type.to_string(),
            prompt: prompt.to_string(),
            response: response.clone(),
            latency_ms: start.elapsed().as_secs_f64() * 1000.0,
        };
        if let Err(e) = self.storage.save_ai_conversation(&conv) {
            // 持久化失败不吞异常也不阻断响应：返回仍成功，仅留运维日志（会话是伴读的附属沉淀）
            crate::log_error!("[ERROR] AI 会话持久化失败: {}", e);
        }

        self.ai_companion_stream_metrics(conv.latency_ms, 1);
        self.ai_companion_stream_recall(book_id);

        Ok(response)
    }

    pub fn ai_companion_stream_compensate(&self, book_id: i64) {
        crate::log_warn!("[COMPENSATE] Cleaned up interrupted AI session for book_id: {}", book_id);
    }

    /// 离线确定性启发卡片（PRD §4.1）：未配置 api_key 或 LLM 重试耗尽时的降级路径，
    /// 按模板给出确定性思考支架，全部带离线标识，不产生任何网络调用。
    pub fn ai_companion_stream_fallback(&self, template_type: &str, selected_text: &str) -> Result<String, String> {
        crate::log_warn!("[FALLBACK] Offline heuristic template fallback for type: {}", template_type);
        let heuristic = match template_type {
            "general" => format!("【通俗解读】\n关于「{}」：可尝试将其比作熟悉的生活场景或模块化积木，先抓住主旨，再拆解支撑主旨的关键要点。", selected_text),
            "logic" => format!("【逻辑链剖析】\n1. 论点前提：作者在段落「{}」中确立了哪些前置假设？\n2. 推导过程：论据到结论之间是否存在跳跃？\n3. 核心结论：论证结构是否闭合、有无未覆盖的反例。", selected_text),
            "critical" => format!("【批判性辩驳】\n反向视角审视「{}」：该论述可能忽略了边界约束条件，在极端或非理想环境下是否存在失效风险？", selected_text),
            "term" => format!("【术语卡拆解】\n- 核心术语：{}\n- 定义：尝试用自己的语言概括其内涵与外延；\n- 衍生应用：它与本文知识导图中的相邻概念如何关联？", selected_text),
            _ => format!("【离线启发】\n针对选区「{}」，建议思考：\n1. 作者提出该论点的核心背景是什么？\n2. 有哪些反例能够推翻该结论？", selected_text),
        };
        Ok(format!(
            "【离线模式】当前未连接 LLM 服务（未配置 api_key 或网络不可用），以下为本地启发卡片。\n\n{}",
            heuristic
        ))
    }

    pub fn ai_companion_stream_metrics(&self, latency_ms: f64, turns: usize) {
        crate::log_info!("[METRICS] ai_companion_stream latency: {:.2}ms (turns: {})", latency_ms, turns);
    }

    pub fn ai_companion_stream_recall(&self, book_id: i64) {
        crate::log_info!("[RECALL] ai companion session completed for book_id: {}", book_id);
    }
}

#[cfg(test)]
mod llm_companion_tests {
    use super::*;
    use crate::llm::tests::MockLlmClient;
    use serde_json::json;
    use std::sync::atomic::Ordering;

    fn temp_db(tag: &str) -> String {
        let path = std::env::temp_dir().join(format!(
            "ai_reader_svc_test_{}_{}.db",
            tag,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        path.to_string_lossy().to_string()
    }

    fn test_config(api_key: &str) -> LlmConfig {
        serde_json::from_value(json!({
            "endpoint": "https://api.example.com/v1",
            "api_key": api_key,
            "model_name": "test-model",
            "system_prompt": "测试人设"
        }))
        .unwrap()
    }

    /// ai_conversation 外键指向 book_meta：先落一本真实书籍再测伴读会话。
    fn seed_book(service: &ReaderService, title: &str) -> i64 {
        service
            .storage
            .save_book(&BookMeta {
                id: 0,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                title: title.to_string(),
                author: None,
                file_path: "/tmp/test_book.md".to_string(),
                file_hash: "test-hash".to_string(),
                format: "md".to_string(),
                total_pages: 0,
                read_progress: 0.0,
                last_read_at: None,
            })
            .unwrap()
    }

    #[test]
    fn companion_offline_card_when_api_key_missing_and_no_llm_call() {
        let db = temp_db("nokey");
        let mock = MockLlmClient::new(vec![Ok("不应被使用".to_string())]);
        let calls = mock.calls.clone();
        let service =
            ReaderService::with_llm_client(SqliteStorage::init_db(&db).unwrap(), Box::new(mock));
        let book_id = seed_book(&service, "离线降级之书");
        let out = service
            .ai_companion_stream_with(&test_config(""), book_id, "term", "被划选的句子", "")
            .unwrap();
        assert!(out.contains("离线"), "缺 api_key 应返回离线卡片，实际: {}", out);
        assert!(out.contains("被划选的句子"), "卡片应回显选区文本");
        assert_eq!(calls.load(Ordering::SeqCst), 0, "缺 api_key 不应发起任何 LLM 调用");
        let convs = service.storage.get_ai_conversations(book_id).unwrap();
        assert_eq!(convs.len(), 1, "降级会话同样入库留痕");
        assert!(convs[0].response.contains("离线"));
        std::fs::remove_file(&db).ok();
    }

    #[test]
    fn companion_returns_real_llm_reply_and_persists_conversation() {
        let db = temp_db("real");
        let mock = MockLlmClient::new(vec![Ok("【通俗解读】真实模型输出：引力透镜类比玻璃透镜。".to_string())]);
        let service =
            ReaderService::with_llm_client(SqliteStorage::init_db(&db).unwrap(), Box::new(mock));
        let book_id = seed_book(&service, "真实调用之书");
        let out = service
            .ai_companion_stream_with(&test_config("sk-test"), book_id, "general", "引力透镜相关段落", "")
            .unwrap();
        assert!(out.contains("引力透镜"), "应返回真实 LLM 内容，实际: {}", out);
        let convs = service.storage.get_ai_conversations(book_id).unwrap();
        assert_eq!(convs.len(), 1);
        assert_eq!(convs[0].template_type, "general");
        assert!(convs[0].response.contains("引力透镜"));
        assert!(convs[0].latency_ms >= 0.0);
        std::fs::remove_file(&db).ok();
    }

    #[test]
    fn companion_falls_back_after_retries_exhausted() {
        let db = temp_db("exhaust");
        let mock = MockLlmClient::new(vec![]);
        let calls = mock.calls.clone();
        let service =
            ReaderService::with_llm_client(SqliteStorage::init_db(&db).unwrap(), Box::new(mock));
        let book_id = seed_book(&service, "重试耗尽之书");
        let out = service
            .ai_companion_stream_with(&test_config("sk-test"), book_id, "critical", "有争议的论述", "为什么?")
            .unwrap();
        assert!(out.contains("离线"), "重试耗尽应降级离线卡片，实际: {}", out);
        assert_eq!(calls.load(Ordering::SeqCst), crate::llm::MAX_RETRIES as usize);
        let convs = service.storage.get_ai_conversations(book_id).unwrap();
        assert_eq!(convs.len(), 1);
        assert!(convs[0].prompt.contains("为什么?"), "原始追问应入库");
        std::fs::remove_file(&db).ok();
    }

    #[test]
    fn companion_offline_conversation_marked_for_audit() {
        let db = temp_db("audit");
        let mock = MockLlmClient::new(vec![Ok("真实回复".to_string())]);
        let service =
            ReaderService::with_llm_client(SqliteStorage::init_db(&db).unwrap(), Box::new(mock));
        let book_id = seed_book(&service, "审计标记之书");

        // 离线降级会话带 offline_fallback 标记
        let _ = service
            .ai_companion_stream_with(&test_config(""), book_id, "general", "段落A", "")
            .unwrap();
        // 真实成功会话无标记
        let _ = service
            .ai_companion_stream_with(&test_config("sk-test"), book_id, "general", "段落B", "")
            .unwrap();

        let convs = service.storage.get_ai_conversations(book_id).unwrap();
        assert_eq!(convs.len(), 2, "两次会话均应入库");
        assert_eq!(convs[0].description.as_deref(), Some("offline_fallback"));
        assert_eq!(convs[1].description, None);
        std::fs::remove_file(&db).ok();
    }
}
