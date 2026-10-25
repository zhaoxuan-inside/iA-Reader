// backend/src/nlp.rs
// 离线三级 NLP 概念图谱计算与分词算法

use std::collections::{HashMap, HashSet};
use crate::domain::{KeywordNode, KeywordRelation};

/// CJK 连续段 → 滑窗二元切词（Lucene CJKAnalyzer 同款策略）。
/// 无词典依赖下对中文关键词/词云最稳：真实词（如「日志」「快照」）因跨语境重复出现
/// 被 TF-IDF/TextRank 自然置顶，一次性拼接 bigram 权重自然衰减。
/// 此前按单字切分，词云呈现孤立汉字，关键词基本不可用。
fn cjk_bigrams(run: &[char], out: &mut Vec<String>) {
    if run.len() < 2 {
        return;
    }
    for i in 0..run.len() - 1 {
        out.push(run[i..i + 2].iter().collect());
    }
}

pub fn tokenize(text: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut current_ascii = String::new();
    let mut current_cjk: Vec<char> = Vec::new();

    let flush_ascii = |current_ascii: &mut String, words: &mut Vec<String>| {
        if !current_ascii.is_empty() {
            words.push(current_ascii.clone());
            current_ascii.clear();
        }
    };

    for c in text.chars() {
        if c.is_ascii_alphanumeric() {
            if !current_cjk.is_empty() {
                cjk_bigrams(&current_cjk, &mut words);
                current_cjk.clear();
            }
            current_ascii.push(c.to_ascii_lowercase());
        } else if is_cjk(c) {
            flush_ascii(&mut current_ascii, &mut words);
            current_cjk.push(c);
        } else {
            flush_ascii(&mut current_ascii, &mut words);
            if !current_cjk.is_empty() {
                cjk_bigrams(&current_cjk, &mut words);
                current_cjk.clear();
            }
        }
    }
    flush_ascii(&mut current_ascii, &mut words);
    if !current_cjk.is_empty() {
        cjk_bigrams(&current_cjk, &mut words);
    }

    // 停用词过滤：单字虚词/常见功能 bigram 与英文虚词一律剔除
    let stopwords: HashSet<&str> = [
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "上", "也",
        "很", "到", "说", "要", "去", "你", "会", "着", "看", "好", "这", "那", "之", "与",
        "一个", "没有", "自己", "我们", "他们", "这个", "那个", "可以", "因为", "所以",
        "但是", "如果", "什么", "已经", "进行", "通过", "以及", "或者", "而且", "然后",
        "就是", "还是", "只是", "非常", "十分", "对于", "关于", "其中", "以上", "以下",
        "是一", "它们", "这样", "那样", "这些", "那些", "时的", "的话",
        "这里", "那里", "哪里", "当时", "此时", "其中",
        "the", "a", "an", "is", "of", "and", "in", "to", "for", "with", "on", "as", "by", "at",
        "it", "be", "this", "that", "are", "was", "or", "we", "he", "she", "his", "her",
    ].iter().cloned().collect();

    words
        .into_iter()
        .filter(|w| {
            // ASCII 单字符（a/I 等）剔除；CJK bigram 天然 2 字符
            w.chars().count() >= 2 && !stopwords.contains(w.as_str())
        })
        .collect()
}

/// CJK 统一表意文字判定（含扩展 A 与兼容表意文字，覆盖常规中文书稿）
fn is_cjk(c: char) -> bool {
    matches!(c,
        '\u{4E00}'..='\u{9FFF}'      // CJK 统一表意文字
        | '\u{3400}'..='\u{4DBF}'    // 扩展 A
        | '\u{F900}'..='\u{FAFF}'    // 兼容表意文字
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn words_of(text: &str) -> Vec<String> {
        tokenize(text)
    }

    #[test]
    fn chinese_yields_bigrams_not_single_chars() {
        let words = words_of("预写式日志保证事务的原子性与持久性");
        assert!(!words.is_empty());
        for w in &words {
            assert_eq!(w.chars().count(), 2, "中文 token 应为二元词: {}", w);
        }
        assert!(words.contains(&"日志".to_string()), "应切出「日志」: {:?}", words);
        assert!(words.contains(&"预写".to_string()), "应切出「预写」: {:?}", words);
    }

    #[test]
    fn repeated_real_words_outrank_junction_bigrams() {
        // 「快照」跨句重复 3 次，拼接 bigram（照隔/离让）仅出现 1 次
        let text = "快照隔离提升并发。快照读取不阻塞。快照视图保持一致。";
        let tokens = words_of(text);
        let counts = |w: &str| tokens.iter().filter(|t| t.as_str() == w).count();
        assert_eq!(counts("快照"), 3);
        assert_eq!(counts("隔离"), 1);
        assert!(counts("快照") > counts("隔离"));
    }

    #[test]
    fn function_bigrams_and_single_chars_filtered() {
        let words = words_of("我是一个人，他在这里。");
        for w in &words {
            assert!(!["是一", "一个", "我在", "这里"].contains(&w.as_str()), "功能词未被过滤: {}", w);
        }
    }

    #[test]
    fn ascii_words_preserved_and_lowercase() {
        let words = words_of("WAL 协议与 MVCC 机制,WAL Protocol");
        assert!(words.contains(&"wal".to_string()));
        assert!(words.contains(&"mvcc".to_string()));
        assert!(words.contains(&"协议".to_string()));
        assert!(!words.iter().any(|w| w.chars().count() == 1), "不得有单字 token: {:?}", words);
    }

    #[test]
    fn mixed_punctuation_splits_runs() {
        let words = words_of("快照隔离、预写式日志。");
        assert!(words.contains(&"快照".to_string()));
        assert!(words.contains(&"日志".to_string()));
        assert!(!words.contains(&"离预".to_string()), "标点应切断跨段 bigram");
    }
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
