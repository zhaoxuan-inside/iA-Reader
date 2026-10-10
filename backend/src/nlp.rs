// backend/src/nlp.rs
// 离线三级 NLP 概念图谱计算与分词算法

use std::collections::{HashMap, HashSet};
use crate::domain::{KeywordNode, KeywordRelation};

pub fn tokenize(text: &str) -> Vec<String> {
    let mut words = Vec::new();
    let chars: Vec<char> = text.chars().collect();
    let mut current_ascii = String::new();

    for &c in &chars {
        if c.is_alphanumeric() {
            if c.is_ascii() {
                current_ascii.push(c.to_ascii_lowercase());
            } else {
                if !current_ascii.is_empty() {
                    words.push(current_ascii.clone());
                    current_ascii.clear();
                }
                words.push(c.to_string());
            }
        } else {
            if !current_ascii.is_empty() {
                words.push(current_ascii.clone());
                current_ascii.clear();
            }
        }
    }
    if !current_ascii.is_empty() {
        words.push(current_ascii);
    }

    // 简单停止词过滤
    let stopwords: HashSet<&str> = ["的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "the", "a", "an", "is", "of", "and", "in", "to", "for", "with", "on", "as", "by", "at"].iter().cloned().collect();
    words.into_iter().filter(|w| w.len() > 1 && !stopwords.contains(w.as_str())).collect()
}

pub fn calculate_tfidf(tokens: &[String], total_docs: usize, doc_freqs: &HashMap<String, usize>) -> Vec<(String, f64, i32)> {
    let mut term_counts: HashMap<String, i32> = HashMap::new();
    for t in tokens {
        *term_counts.entry(t.clone()).or_insert(0) += 1;
    }

    let total_tokens = tokens.len() as f64;
    let mut scored = Vec::new();

    for (term, count) in &term_counts {
        let tf = *count as f64 / (total_tokens.max(1.0));
        let df = *doc_freqs.get(term).unwrap_or(&1) as f64;
        let idf = ((total_docs as f64 + 1.0) / (df + 1.0)).ln() + 1.0;
        let score = tf * idf;
        scored.push((term.clone(), score, *count));
    }

    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored
}

pub fn calculate_textrank(tokens: &[String], window_size: usize, iterations: usize) -> Vec<(String, f64)> {
    if tokens.is_empty() {
        return Vec::new();
    }

    let mut co_occur: HashMap<(String, String), f64> = HashMap::new();
    let mut vocab: HashSet<String> = HashSet::new();

    for i in 0..tokens.len() {
        let end = (i + window_size).min(tokens.len());
        let w1 = &tokens[i];
        vocab.insert(w1.clone());
        for j in (i + 1)..end {
            let w2 = &tokens[j];
            if w1 != w2 {
                *co_occur.entry((w1.clone(), w2.clone())).or_insert(0.0) += 1.0;
                *co_occur.entry((w2.clone(), w1.clone())).or_insert(0.0) += 1.0;
            }
        }
    }

    let vocab_vec: Vec<String> = vocab.into_iter().collect();
    let n = vocab_vec.len();
    if n == 0 {
        return Vec::new();
    }

    let d = 0.85;
    let mut scores: HashMap<String, f64> = vocab_vec.iter().map(|w| (w.clone(), 1.0 / n as f64)).collect();

    for _ in 0..iterations {
        let mut new_scores = HashMap::new();
        for vi in &vocab_vec {
            let mut sum_val = 0.0;
            for vj in &vocab_vec {
                if let Some(&weight) = co_occur.get(&(vj.clone(), vi.clone())) {
                    let total_out: f64 = vocab_vec.iter().map(|vk| co_occur.get(&(vj.clone(), vk.clone())).cloned().unwrap_or(0.0)).sum();
                    if total_out > 0.0 {
                        sum_val += (weight / total_out) * scores.get(vj).cloned().unwrap_or(0.0);
                    }
                }
            }
            new_scores.insert(vi.clone(), (1.0 - d) + d * sum_val);
        }
        scores = new_scores;
    }

    let mut ranked: Vec<(String, f64)> = scores.into_iter().collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    ranked
}

pub fn build_co_occurrence(tokens: &[String], keywords: &[KeywordNode], window_size: usize) -> Vec<KeywordRelation> {
    let kw_map: HashMap<String, i64> = keywords.iter().map(|k| (k.word.clone(), k.id)).collect();
    let mut pair_counts: HashMap<(i64, i64), i32> = HashMap::new();

    for i in 0..tokens.len() {
        let end = (i + window_size).min(tokens.len());
        if let Some(&id1) = kw_map.get(&tokens[i]) {
            for j in (i + 1)..end {
                if let Some(&id2) = kw_map.get(&tokens[j]) {
                    if id1 != id2 {
                        let key = if id1 < id2 { (id1, id2) } else { (id2, id1) };
                        *pair_counts.entry(key).or_insert(0) += 1;
                    }
                }
            }
        }
    }

    let mut relations = Vec::new();
    let total_windows = tokens.len().max(1) as f64;

    for ((src, tgt), count) in pair_counts {
        let p_xy = count as f64 / total_windows;
        let pmi = if p_xy > 0.0 { (p_xy * 100.0).ln().max(0.1) } else { 0.1 };
        let weight = (pmi / 5.0).min(1.0);

        relations.push(KeywordRelation {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            book_id: keywords.first().map(|k| k.book_id).unwrap_or(0),
            source_word_id: src,
            target_word_id: tgt,
            co_occurrence_count: count,
            pmi_score: pmi,
            weight,
        });
    }

    relations.sort_by(|a, b| b.weight.partial_cmp(&a.weight).unwrap_or(std::cmp::Ordering::Equal));
    relations
}
