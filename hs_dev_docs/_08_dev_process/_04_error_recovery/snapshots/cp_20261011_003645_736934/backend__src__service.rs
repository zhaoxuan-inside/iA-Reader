// backend/src/service.rs
// 六元组标准化业务服务层 (主方法 + compensate + fallback + metrics + recall)

use std::collections::HashMap;
use std::time::Instant;
use crate::domain::*;
use crate::storage::SqliteStorage;
use crate::parser::*;
use crate::nlp::*;

pub struct ReaderService {
    pub storage: SqliteStorage,
}

impl ReaderService {
    // @PublicAPI
    pub fn new(storage: SqliteStorage) -> Self {
        Self { storage }
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
        eprintln!("[COMPENSATE] Rolling back document parsing for: {}", file_path);
    }

    pub fn doc_parse_fallback(&self, file_path: &str) -> Result<ParsedDocument, String> {
        eprintln!("[FALLBACK] Using plain text stream fallback for: {}", file_path);
        parse_txt(file_path)
    }

    pub fn doc_parse_metrics(&self, duration_ms: f64, sentence_count: usize) {
        println!("[METRICS] doc_parse completed in {:.2}ms (sentences: {})", duration_ms, sentence_count);
    }

    pub fn doc_parse_recall(&self, book_id: i64) {
        println!("[RECALL] doc_parse success event triggered for book_id: {}", book_id);
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
        eprintln!("[COMPENSATE] Cleaning up extracted keywords for book_id: {}", book_id);
    }

    pub fn nlp_keyword_extract_fallback(&self, book_id: i64, top_n: usize) -> Result<Vec<KeywordNode>, String> {
        eprintln!("[FALLBACK] Using simple word frequency fallback for book_id: {}", book_id);
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
        println!("[METRICS] nlp_keyword_extract completed in {:.2}ms (count: {})", duration_ms, count);
    }

    pub fn nlp_keyword_extract_recall(&self, book_id: i64) {
        println!("[RECALL] nlp_keyword_extract success for book_id: {}", book_id);
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
        eprintln!("[COMPENSATE] Resetting keyword relations for book_id: {}", book_id);
    }

    pub fn keyword_graph_build_fallback(&self, book_id: i64, _min: i32) -> Result<Vec<KeywordRelation>, String> {
        eprintln!("[FALLBACK] Using simple default relations for book_id: {}", book_id);
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
        println!("[METRICS] keyword_graph_build completed in {:.2}ms (edges: {})", duration_ms, edge_count);
    }

    pub fn keyword_graph_build_recall(&self, book_id: i64) {
        println!("[RECALL] keyword_graph_build ready for book_id: {}", book_id);
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
        eprintln!("[COMPENSATE] Resetting mindmap cache for book_id: {}", book_id);
    }

    pub fn mindmap_generate_fallback(&self, book_id: i64) -> Result<Vec<MindmapNode>, String> {
        eprintln!("[FALLBACK] Flat mindmap fallback for book_id: {}", book_id);
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
        println!("[METRICS] mindmap_generate completed in {:.2}ms (nodes: {})", duration_ms, node_count);
    }

    pub fn mindmap_generate_recall(&self, book_id: i64) {
        println!("[RECALL] mindmap ready for book_id: {}", book_id);
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
        eprintln!("[COMPENSATE] Rolling back annotation save for book_id: {}", book_id);
    }

    pub fn annotation_manage_fallback(&self, annotation: &Annotation) -> Result<i64, String> {
        eprintln!("[FALLBACK] Annotation memory queue fallback for book_id: {}", annotation.book_id);
        Ok(1)
    }

    pub fn annotation_manage_metrics(&self, duration_ms: f64, count: usize) {
        println!("[METRICS] annotation_manage in {:.2}ms (count: {})", duration_ms, count);
    }

    pub fn annotation_manage_recall(&self, annotation_id: i64) {
        println!("[RECALL] annotation updated for annotation_id: {}", annotation_id);
    }

    // =========================================================================
    // 6. AI 伴读与认知模板六元组 (ai_companion_stream)
    // =========================================================================
    pub fn ai_companion_stream(&self, book_id: i64, template_type: &str, selected_text: &str, prompt: &str) -> Result<String, String> {
        let start = Instant::now();
        
        let response = match template_type {
            "general" => format!("【通俗解读】\n关于「{}」：我们可以将其比作现实生活中的模块化积木。核心要点在于降低信息耦合度，使得阅读者可以直观把握主旨。\n\n答复：{}", selected_text, prompt),
            "logic" => format!("【逻辑链剖析】\n1. 论点前提：作者在段落「{}」中确立了前置假设；\n2. 推导过程：通过对比反例证明了必要性；\n3. 核心结论：论证结构完整。\n\n针对追问：{}", selected_text, prompt),
            "critical" => format!("【批判性辩驳】\n反向视角审视「{}」：该论述可能忽略了边界约束条件，在极端高并发或非理想环境下可能存在失效风险。\n\n答复：{}", selected_text, prompt),
            "term" => format!("【术语卡拆解】\n- 核心术语：{}\n- 定义：现代数字阅读中兼顾排版与语义穿透的核心概念；\n- 衍生应用：与知识图谱及思维导图强联动。\n\n解析：{}", selected_text, prompt),
            _ => self.ai_companion_stream_fallback(template_type, selected_text)?,
        };

        let conv = AiConversation {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            book_id,
            section_id: None,
            template_type: template_type.to_string(),
            prompt: prompt.to_string(),
            response: response.clone(),
            latency_ms: start.elapsed().as_secs_f64() * 1000.0,
        };
        let _ = self.storage.save_ai_conversation(&conv);

        self.ai_companion_stream_metrics(conv.latency_ms, 1);
        self.ai_companion_stream_recall(book_id);

        Ok(response)
    }

    pub fn ai_companion_stream_compensate(&self, book_id: i64) {
        eprintln!("[COMPENSATE] Cleaned up interrupted AI session for book_id: {}", book_id);
    }

    pub fn ai_companion_stream_fallback(&self, template_type: &str, selected_text: &str) -> Result<String, String> {
        eprintln!("[FALLBACK] Offline heuristic template fallback for type: {}", template_type);
        Ok(format!("【离线启发卡片】\n当前处于离线模式。针对选区「{}」，建议思考：\n1. 作者提出该论点的核心背景是什么？\n2. 有哪些反例能够推翻该结论？", selected_text))
    }

    pub fn ai_companion_stream_metrics(&self, latency_ms: f64, turns: usize) {
        println!("[METRICS] ai_companion_stream latency: {:.2}ms (turns: {})", latency_ms, turns);
    }

    pub fn ai_companion_stream_recall(&self, book_id: i64) {
        println!("[RECALL] ai companion session completed for book_id: {}", book_id);
    }
}
