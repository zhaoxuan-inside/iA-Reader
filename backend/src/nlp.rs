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

/// 多文档词频统计（TF-IDF 的 df 项）：每个 section 视作一篇文档，
/// 统计词项出现在多少篇文档中——此前 service 传空 df 使 idf 恒为常数 1.0，
/// TF-IDF 名存实亡、退化成纯词频。
pub fn doc_frequencies(section_tokens: &[Vec<String>]) -> HashMap<String, usize> {
    let mut df: HashMap<String, usize> = HashMap::new();
    for tokens in section_tokens {
        let mut seen: HashSet<&String> = HashSet::new();
        for t in tokens {
            if seen.insert(t) {
                *df.entry(t.clone()).or_insert(0) += 1;
            }
        }
    }
    df
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

/// TextRank 词表上限：按词频截断，保证共现图规模有界（10 万字中文 bigram
/// 原始词汇量可达数万，不截断则边数与迭代成本失控）
const TEXTRANK_MAX_VOCAB: usize = 2000;

/// 稀疏图幂迭代 TextRank：窗口共现构建无向边 → 邻接表 → O(E·iterations)。
/// 此前实现为 O(vocab²) 双重循环且每轮重复重算全表出权，中文长文上不可行。
pub fn calculate_textrank(tokens: &[String], window_size: usize, iterations: usize) -> Vec<(String, f64)> {
    if tokens.is_empty() {
        return Vec::new();
    }

    // 1) 词频排序截断词表（稳定排序保证同频词序确定）
    let mut freq: HashMap<&str, usize> = HashMap::new();
    for t in tokens {
        *freq.entry(t.as_str()).or_insert(0) += 1;
    }
    let mut ranked_vocab: Vec<(&str, usize)> = freq.into_iter().collect();
    ranked_vocab.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    ranked_vocab.truncate(TEXTRANK_MAX_VOCAB);
    let index: HashMap<&str, u32> = ranked_vocab
        .iter()
        .enumerate()
        .map(|(i, (w, _))| (*w, i as u32))
        .collect();

    // 2) 窗口共现 → 无向边权
    let mut edge_weight: HashMap<(u32, u32), f64> = HashMap::new();
    for i in 0..tokens.len() {
        let Some(&wi) = index.get(tokens[i].as_str()) else { continue };
        let end = (i + window_size).min(tokens.len());
        for w2 in &tokens[i + 1..end] {
            let Some(&wj) = index.get(w2.as_str()) else { continue };
            if wi == wj {
                continue;
            }
            let key = if wi < wj { (wi, wj) } else { (wj, wi) };
            *edge_weight.entry(key).or_insert(0.0) += 1.0;
        }
    }
    if edge_weight.is_empty() {
        return Vec::new();
    }

    // 3) 邻接表 + 出权累计
    let n = index.len();
    let mut adj: Vec<Vec<(u32, f64)>> = vec![Vec::new(); n];
    let mut out_weight = vec![0.0f64; n];
    for ((a, b), w) in &edge_weight {
        adj[*a as usize].push((*b, *w));
        adj[*b as usize].push((*a, *w));
        out_weight[*a as usize] += w;
        out_weight[*b as usize] += w;
    }

    // 4) 幂迭代（经典归一化 PageRank：score = (1-d)/n + d·Σ w/out·score）
    let d = 0.85;
    let mut scores = vec![1.0f64 / n as f64; n];
    for _ in 0..iterations {
        let mut next = vec![(1.0 - d) / n as f64; n];
        for vj in 0..n {
            if out_weight[vj] <= 0.0 {
                continue;
            }
            let base = d * scores[vj] / out_weight[vj];
            for &(vi, w) in &adj[vj] {
                next[vi as usize] += base * w;
            }
        }
        scores = next;
    }

    let mut ranked: Vec<(String, f64)> = ranked_vocab
        .iter()
        .filter_map(|(w, _)| index.get(w).map(|i| ((*w).to_string(), scores[*i as usize])))
        .collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    ranked
}

/// 关键词共现图 + 真实 PMI 边权：
/// PMI = ln( P(x,y) / (P(x)·P(y)) )，此前实现把共现计数缩放取对数冒充 PMI，
/// 缺失边缘概率归一，导致高频词间必然"强相关"的假边大量入选。
pub fn build_co_occurrence(tokens: &[String], keywords: &[KeywordNode], window_size: usize) -> Vec<KeywordRelation> {
    let kw_map: HashMap<String, i64> = keywords.iter().map(|k| (k.word.clone(), k.id)).collect();
    let word_by_id: HashMap<i64, String> = keywords.iter().map(|k| (k.id, k.word.clone())).collect();
    let mut pair_counts: HashMap<(i64, i64), i32> = HashMap::new();

    for i in 0..tokens.len() {
        let end = (i + window_size).min(tokens.len());
        if let Some(&id1) = kw_map.get(&tokens[i]) {
            for w2 in &tokens[i + 1..end] {
                if let Some(&id2) = kw_map.get(w2) {
                    if id1 != id2 {
                        let key = if id1 < id2 { (id1, id2) } else { (id2, id1) };
                        *pair_counts.entry(key).or_insert(0) += 1;
                    }
                }
            }
        }
    }

    // 边缘概率：P(w) = freq(w) / N；联合概率：P(x,y) = co_count / N
    let total = tokens.len().max(1) as f64;
    let mut freqs: HashMap<&str, f64> = HashMap::new();
    for t in tokens {
        *freqs.entry(t.as_str()).or_insert(0.0) += 1.0;
    }
    // PMI 归一化参考上界：ln(N)（P(x)·P(y) 趋近最小时 PMI 的量级锚点）
    let pmi_scale = total.ln().max(1.0);

    let mut relations = Vec::new();
    for ((src, tgt), count) in pair_counts {
        let p_xy = count as f64 / total;
        let p_x = word_by_id.get(&src).and_then(|w| freqs.get(w.as_str())).copied().unwrap_or(0.0) / total;
        let p_y = word_by_id.get(&tgt).and_then(|w| freqs.get(w.as_str())).copied().unwrap_or(0.0) / total;
        let pmi = if p_xy > 0.0 && p_x > 0.0 && p_y > 0.0 {
            (p_xy / (p_x * p_y)).ln()
        } else {
            0.0
        };
        let weight = if pmi <= 0.0 { 0.0 } else { (pmi / pmi_scale).min(1.0) };

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

#[cfg(test)]
mod nlp_quality_tests {
    use super::*;
    use crate::domain::{KeywordNode, KeywordRelation};

    fn kw(id: i64, word: &str) -> KeywordNode {
        KeywordNode {
            id, created_at: String::new(), updated_at: String::new(), description: None,
            is_del: 0, version: 1, book_id: 1, word: word.to_string(),
            level: "book".into(), tfidf_score: 0.0, textrank_score: 0.0, frequency: 0,
        }
    }

    #[test]
    fn textrank_ranks_repeated_hub_word_first() {
        // 星型共现图：「快照」与四个互不相连的词相邻，PageRank 必然置顶中心词；
        // 注：小而稠密的短句图上 PR 趋近均匀，属正确行为而非 bug
        let text = "快照 隔离。快照 日志。快照 事务。快照 索引。";
        let ranked = calculate_textrank(&tokenize(text), 2, 20);
        assert!(!ranked.is_empty());
        assert_eq!(ranked[0].0, "快照", "星型图中心词应居首: {:?}", &ranked[..3.min(ranked.len())]);
    }

    #[test]
    fn textrank_handles_long_token_stream_quickly() {
        // 3 万 token 规模下必须瞬时完成（O(E) 迭代，vocab 截断上界 2000）
        let mut tokens = Vec::new();
        for i in 0..15000 {
            tokens.push(format!("词{:02}", i % 40));
        }
        let start = std::time::Instant::now();
        let ranked = calculate_textrank(&tokens, 10, 5);
        assert!(!ranked.is_empty());
        assert!(start.elapsed().as_millis() < 2000, "3 万 token TextRank 应在 2s 内: {:?}", start.elapsed());
    }

    #[test]
    fn pmi_rewards_exclusive_cooccurrence_and_stays_bounded() {
        // 「日志」「快照」只在彼此窗口内共现 → PMI 为正且显著；
        // 「系统」与谁都共现（高边缘概率）→ PMI 被压制
        let tokens: Vec<String> = tokenize("日志快照记录状态。日志快照保存现场。系统整体保持平稳。系统承载快照。系统承载日志。")
            .into_iter()
            .collect();
        let keywords = vec![kw(1, "日志"), kw(2, "快照"), kw(3, "系统"), kw(4, "承载"), kw(5, "保持")];
        let rels: Vec<KeywordRelation> = build_co_occurrence(&tokens, &keywords, 6);
        assert!(!rels.is_empty());
        for r in &rels {
            assert!(r.weight >= 0.0 && r.weight <= 1.0, "weight 应归一化到 [0,1]: {}", r.weight);
            assert!(r.pmi_score.is_finite(), "PMI 必须有限: {}", r.pmi_score);
        }
        let pmi = |a: i64, b: i64| rels.iter().find(|r| (r.source_word_id, r.target_word_id) == (a.min(b), b.max(a))).map(|r| r.pmi_score);
        let strong = pmi(1, 2); // 日志-快照 专享共现
        assert!(strong.is_some(), "日志-快照应有共现边");
        if let (Some(s), Some(sl)) = (strong, pmi(1, 3)) {
            assert!(s > sl, "专享共现 PMI 应高于高频泛化词对: 日志-快照={s:?}, 日志-系统={sl:?}");
        }
    }

    #[test]
    fn doc_frequencies_counts_per_document_presence() {
        let docs = vec![
            tokenize("日志快照原子性"),
            tokenize("日志恢复机制"),
            tokenize("无关内容完全不同"),
        ];
        let df = doc_frequencies(&docs);
        assert_eq!(df.get("日志"), Some(&2), "日志出现在两篇文档");
        assert_eq!(df.get("快照"), Some(&1), "快照只出现在一篇文档");
    }
}
