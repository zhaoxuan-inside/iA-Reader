// backend/src/parser.rs
// 全格式统一文档解构适配器 (Markdown / TXT)
//
// MVP 冻结范围（ai_reader_phased_plan.md CEO Cut C5）：仅 Markdown + TXT。
// PDF / EPUB 显式拒绝并返回明确错误，禁止返回任何占位正文——
// 此前此处以硬编码假论文/假章节"成功"入库，掩盖了格式缺口。
//
// 结构化产出（FEAT-002 三级 AST）：章节（H1-H6 层级树）→ 段落（空行分块，
// 代码围栏整块保留）→ 句子（中英文终止符切句）。char_offset 均为全文绝对
// 字符偏移；此前句子按非空行切片且坐标是章节内局部值，"句子"名不副实。

use std::fs;
use std::path::Path;
use sha2::{Digest, Sha256};
use crate::domain::{BookMeta, BookSection, ParagraphNode, SentenceNode};

/// 导入拦截上限：20MB（FEAT-001 REQ-003 分支 4）
const MAX_IMPORT_BYTES: usize = 20 * 1024 * 1024;

#[derive(Debug)]
pub struct ParsedDocument {
    pub meta: BookMeta,
    pub sections: Vec<BookSection>,
    pub paragraphs: Vec<ParagraphNode>,
    pub sentences: Vec<SentenceNode>,
}

/// 拒绝 MVP 范围外格式的统一错误口径
fn unsupported_format(display: &str) -> String {
    format!(
        "暂不支持 {} 解析：MVP 范围为 Markdown/TXT，该格式将在后续版本支持",
        display
    )
}

pub fn parse_pdf(file_path: &str) -> Result<ParsedDocument, String> {
    let path = Path::new(file_path);
    if !path.exists() {
        return Err(format!("PDF file not found: {}", file_path));
    }
    Err(unsupported_format("PDF"))
}

pub fn parse_epub(file_path: &str) -> Result<ParsedDocument, String> {
    let path = Path::new(file_path);
    if !path.exists() {
        return Err(format!("EPUB file not found: {}", file_path));
    }
    Err(unsupported_format("EPUB"))
}

fn file_sha256(file_path: &str) -> Result<String, String> {
    let bytes = fs::read(file_path).map_err(|e| format!("无法读取文件 {}: {}", file_path, e))?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    Ok(format!("{:x}", hasher.finalize()))
}

/// 导入通用前置校验：空文件与超限文件显式报错（此前空文件会成功入库单节"正文"）
fn validate_source(content: &str) -> Result<(), String> {
    if content.trim().is_empty() {
        return Err("文件内容为空，无法导入".to_string());
    }
    if content.len() > MAX_IMPORT_BYTES {
        return Err(format!(
            "文件超过 {}MB 导入上限（当前约 {}MB）",
            MAX_IMPORT_BYTES / (1024 * 1024),
            content.len() / (1024 * 1024)
        ));
    }
    Ok(())
}

fn estimate_pages(content: &str) -> i32 {
    // 版心按每页约 1500 字估算；MD/TXT 无物理分页，仅作展示参考值
    (((content.chars().count() as i32) + 1499) / 1500).max(1)
}

fn new_section(book_id: i64, index: i32, title: String, level: i32, parent_id: Option<i64>, total_pages: i32, content: String) -> BookSection {
    BookSection {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: None,
        is_del: 0,
        version: 1,
        book_id,
        section_index: index,
        title,
        level,
        parent_id,
        start_page: 1,
        end_page: total_pages,
        content: Some(content),
    }
}

fn new_paragraph(book_id: i64, section_pos: i64, index: i32, text: String, page_number: i32, start: i32, end: i32) -> ParagraphNode {
    ParagraphNode {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: None,
        is_del: 0,
        version: 1,
        book_id,
        section_id: section_pos,
        paragraph_index: index,
        text,
        page_number,
        char_offset_start: start,
        char_offset_end: end,
    }
}

fn new_sentence(book_id: i64, section_pos: i64, index: i32, text: String, page_number: i32, start: i32, end: i32) -> SentenceNode {
    SentenceNode {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: None,
        is_del: 0,
        version: 1,
        book_id,
        section_id: section_pos,
        sentence_index: index,
        text,
        page_number,
        char_offset_start: start,
        char_offset_end: end,
    }
}

/// 段落内切句：终止符 。！？!?…；后必断；ASCII '.' 仅在后随空白/串尾且非小数点时断句，
/// 过短片段（<2 字符）并入前句避免碎片。
fn split_sentences(text: &str) -> Vec<(String, usize)> {
    let chars: Vec<char> = text.chars().collect();
    let mut out: Vec<(String, usize)> = Vec::new();
    let mut start = 0usize;
    let mut i = 0usize;
    let is_terminal = |c: char, next: Option<char>| -> bool {
        match c {
            '。' | '！' | '？' | '!' | '?' | '…' => true,
            ';' | '；' => false,
            '.' => match next {
                None => true,
                Some(n) => n.is_whitespace(),
            },
            _ => false,
        }
    };
    while i < chars.len() {
        let c = chars[i];
        if is_terminal(c, chars.get(i + 1).copied()) {
            let end = i + 1;
            let seg: String = chars[start..end].iter().collect();
            let trimmed = seg.trim();
            if !trimmed.is_empty() {
                out.push((trimmed.to_string(), start));
            }
            start = end;
        }
        i += 1;
    }
    if start < chars.len() {
        let seg: String = chars[start..].iter().collect();
        let trimmed = seg.trim();
        if !trimmed.is_empty() {
            out.push((trimmed.to_string(), start));
        }
    }
    // 过短片段并入前句（保持锚点连续）
    let mut merged: Vec<(String, usize)> = Vec::new();
    for (text, s) in out {
        if text.chars().count() < 2 {
            if let Some(last) = merged.last_mut() {
                last.0.push_str(&text);
                continue;
            }
        }
        merged.push((text, s));
    }
    merged
}

/// 段落行块：正文按空行切块；代码围栏（``` / ~~~）整块保留不切段。
struct LineBlock {
    text: String,
    /// 块首行在全文中的字符偏移
    start_offset: i32,
}

/// 将一段正文按空行切为段落行块
fn split_paragraph_blocks(body: &str, body_start_offset: i32) -> Vec<LineBlock> {
    let mut blocks: Vec<LineBlock> = Vec::new();
    let mut cur_lines: Vec<String> = Vec::new();
    let mut cur_start: Option<i32> = None;
    let mut offset = body_start_offset;
    let mut fence: Option<char> = None;

    let flush = |cur_lines: &mut Vec<String>, cur_start: &mut Option<i32>, blocks: &mut Vec<LineBlock>, end_offset: i32| {
        if cur_lines.is_empty() {
            *cur_start = None;
            return;
        }
        let text = cur_lines.join("\n").trim().to_string();
        if !text.is_empty() {
            blocks.push(LineBlock {
                text,
                start_offset: cur_start.unwrap_or(end_offset),
            });
        }
        cur_lines.clear();
        *cur_start = None;
    };

    for line in body.lines() {
        let trimmed = line.trim_start();
        // 围栏开/闭切换：```（可带信息串）或 ~~~
        let marker = if trimmed.starts_with("```") {
            Some('`')
        } else if trimmed.starts_with("~~~") {
            Some('~')
        } else {
            None
        };
        if let Some(m) = marker {
            match fence {
                None => fence = Some(m),
                Some(f) if f == m => fence = None,
                _ => {}
            }
        }
        let is_blank = line.trim().is_empty();
        if is_blank && fence.is_none() {
            flush(&mut cur_lines, &mut cur_start, &mut blocks, offset);
        } else {
            if cur_start.is_none() {
                cur_start = Some(offset);
            }
            cur_lines.push(line.to_string());
        }
        offset += line.chars().count() as i32 + 1; // +1 计换行
    }
    flush(&mut cur_lines, &mut cur_start, &mut blocks, offset);
    blocks
}

/// Markdown 行分类：ATX 标题（1-6 级）需位于代码围栏之外
fn atx_heading(line: &str) -> Option<(i32, String)> {
    let trimmed = line.trim_start();
    let level = trimmed.chars().take_while(|&c| c == '#').count();
    if !(1..=6).contains(&level) {
        return None;
    }
    let rest = &trimmed[level..];
    if rest.is_empty() || !rest.starts_with(' ') {
        return None;
    }
    let title = rest.trim().trim_end_matches('#').trim().to_string();
    if title.is_empty() {
        return None;
    }
    Some((level as i32, title))
}

/// Markdown 结构化解析：H1-H6 层级树 + 段落块 + 句子切片
fn build_markdown_document(content: &str, book_id: i64, total_pages: i32) -> (Vec<BookSection>, Vec<ParagraphNode>, Vec<SentenceNode>) {
    // Pass 1：按标题行切节（代码围栏内的 '#' 不是标题）
    struct RawSection {
        title: String,
        level: i32,
        body: String,
        body_start_offset: i32,
    }
    let mut raws: Vec<RawSection> = Vec::new();
    let mut cur = RawSection { title: String::new(), level: 1, body: String::new(), body_start_offset: 0 };
    let mut offset = 0i32;
    let mut fence: Option<char> = None;
    for line in content.lines() {
        let trimmed = line.trim_start();
        let marker = if trimmed.starts_with("```") {
            Some('`')
        } else if trimmed.starts_with("~~~") {
            Some('~')
        } else {
            None
        };
        if let Some(m) = marker {
            match fence {
                None => fence = Some(m),
                Some(f) if f == m => fence = None,
                _ => {}
            }
        } else if fence.is_none() {
            if let Some((level, title)) = atx_heading(line) {
                // 空前置段（无标题且无正文）不入列，避免多余的"正文"空节
                if !cur.title.is_empty() || !cur.body.trim().is_empty() {
                    raws.push(RawSection {
                        title: std::mem::take(&mut cur.title),
                        level: cur.level,
                        body: std::mem::take(&mut cur.body),
                        body_start_offset: cur.body_start_offset,
                    });
                }
                cur = RawSection { title, level, body: String::new(), body_start_offset: offset + line.chars().count() as i32 + 1 };
                offset += line.chars().count() as i32 + 1;
                continue;
            }
        }
        cur.body.push_str(line);
        cur.body.push('\n');
        offset += line.chars().count() as i32 + 1;
    }
    raws.push(RawSection {
        title: std::mem::take(&mut cur.title),
        level: cur.level,
        body: std::mem::take(&mut cur.body),
        body_start_offset: cur.body_start_offset,
    });

    // Pass 2：层级树（栈式回溯 parent）+ 段落 + 句子
    let mut sections: Vec<BookSection> = Vec::new();
    let mut paragraphs: Vec<ParagraphNode> = Vec::new();
    let mut sentences: Vec<SentenceNode> = Vec::new();
    // (level, section 序号 1-based)：栈顶为当前最近祖先
    let mut stack: Vec<(i32, i64)> = Vec::new();

    for (idx, raw) in raws.iter().enumerate() {
        let pos = (idx + 1) as i64;
        while let Some(&(lv, _)) = stack.last() {
            if lv >= raw.level {
                stack.pop();
            } else {
                break;
            }
        }
        let parent = stack.last().map(|&(_, p)| p);
        let title = if raw.title.is_empty() { "正文".to_string() } else { raw.title.clone() };
        stack.push((raw.level, pos));

        let section = new_section(book_id, pos as i32, title, raw.level, parent, total_pages, raw.body.clone());
        sections.push(section);

        let mut para_index = 0i32;
        for block in split_paragraph_blocks(&raw.body, raw.body_start_offset) {
            para_index += 1;
            let len = block.text.chars().count() as i32;
            paragraphs.push(new_paragraph(
                book_id,
                pos,
                para_index,
                block.text.clone(),
                1,
                block.start_offset,
                block.start_offset + len,
            ));
            for (sent, inner) in split_sentences(&block.text) {
                let slen = sent.chars().count() as i32;
                if slen == 0 {
                    continue;
                }
                sentences.push(new_sentence(
                    book_id,
                    pos,
                    sentences.len() as i32 + 1,
                    sent,
                    1,
                    block.start_offset + inner as i32,
                    block.start_offset + inner as i32 + slen,
                ));
            }
        }
    }

    (sections, paragraphs, sentences)
}

pub fn parse_markdown(file_path: &str) -> Result<ParsedDocument, String> {
    let content = fs::read_to_string(file_path)
        .map_err(|e| format!("无法读取 Markdown 文件 {}: {}", file_path, e))?;
    validate_source(&content)?;
    let path = Path::new(file_path);
    let title = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
    let file_hash = file_sha256(file_path)?;
    let total_pages = estimate_pages(&content);

    let meta = BookMeta {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: Some("Markdown 文档".to_string()),
        is_del: 0,
        version: 1,
        title,
        author: None,
        file_path: file_path.to_string(),
        file_hash,
        format: "md".to_string(),
        total_pages,
        read_progress: 0.0,
        last_read_at: None,
        read_section_id: None,
        read_paragraph_index: 0,
        read_char_offset: 0,
    };

    let (sections, paragraphs, sentences) = build_markdown_document(&content, 0, total_pages);
    Ok(ParsedDocument { meta, sections, paragraphs, sentences })
}

pub fn parse_txt(file_path: &str) -> Result<ParsedDocument, String> {
    let content = fs::read_to_string(file_path)
        .map_err(|e| format!("无法读取文本文件 {}: {}", file_path, e))?;
    validate_source(&content)?;
    let path = Path::new(file_path);
    let title = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
    let file_hash = file_sha256(file_path)?;
    let total_pages = estimate_pages(&content);

    let meta = BookMeta {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: Some("纯文本文档".to_string()),
        is_del: 0,
        version: 1,
        title,
        author: None,
        file_path: file_path.to_string(),
        file_hash,
        format: "txt".to_string(),
        total_pages,
        read_progress: 0.0,
        last_read_at: None,
        read_section_id: None,
        read_paragraph_index: 0,
        read_char_offset: 0,
    };

    let (sections, paragraphs, sentences) = build_markdown_document(&content, 0, total_pages);
    Ok(ParsedDocument { meta, sections, paragraphs, sentences })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_tmp(name: &str, content: &str) -> String {
        let dir = std::env::temp_dir().join(format!("ai_reader_parser_{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join(name);
        fs::write(&p, content).unwrap();
        p.to_string_lossy().to_string()
    }

    #[test]
    fn pdf_is_rejected_without_fabricated_content() {
        let p = write_tmp("fake.pdf", "%PDF-1.4 fake");
        let err = parse_pdf(&p).unwrap_err();
        assert!(err.contains("暂不支持"), "错误应说明不支持: {}", err);
    }

    #[test]
    fn empty_file_is_rejected() {
        let p = write_tmp("empty.md", "   \n\n  ");
        let err = parse_markdown(&p).unwrap_err();
        assert!(err.contains("为空"), "空文件应显式拦截: {}", err);
    }

    #[test]
    fn h1_to_h6_build_hierarchy_tree() {
        let p = write_tmp(
            "tree.md",
            "# 甲章\n甲正文。\n\n## 甲·小节一\n小节正文。\n\n### 深入点\n深层正文。\n\n## 甲·小节二\n另一节。\n\n# 乙章\n乙正文。\n",
        );
        let doc = parse_markdown(&p).unwrap();
        let titles: Vec<(String, i32)> = doc.sections.iter().map(|s| (s.title.clone(), s.level)).collect();
        assert_eq!(
            titles,
            vec![
                ("甲章".into(), 1),
                ("甲·小节一".into(), 2),
                ("深入点".into(), 3),
                ("甲·小节二".into(), 2),
                ("乙章".into(), 1),
            ],
            "H1-H6 应全部成节: {:?}",
            titles
        );
        // 层级树 parent 断言：小节一 parent=甲章(1)，深入点 parent=小节一(2)，甲·小节二 parent=甲章(1)
        assert_eq!(doc.sections[1].parent_id, Some(1));
        assert_eq!(doc.sections[2].parent_id, Some(2));
        assert_eq!(doc.sections[3].parent_id, Some(1));
        assert_eq!(doc.sections[4].parent_id, None);
    }

    #[test]
    fn headings_inside_code_fence_are_body_text() {
        let p = write_tmp(
            "fence.md",
            "# 正章\n```bash\n# 这不是标题\necho hi\n```\n后续正文。\n",
        );
        let doc = parse_markdown(&p).unwrap();
        assert_eq!(doc.sections.len(), 1, "围栏内的 # 不得切节: {:?}", doc.sections.iter().map(|s| &s.title).collect::<Vec<_>>());
        assert!(doc.paragraphs.iter().any(|p| p.text.contains("echo hi")));
    }

    #[test]
    fn paragraphs_are_blank_line_blocks_with_absolute_offsets() {
        let p = write_tmp(
            "para.md",
            "# 甲章\n第一段第一行。\n第一段第二行。\n\n第二段。\n\n# 乙章\n乙段落。\n",
        );
        let doc = parse_markdown(&p).unwrap();
        let sec1_paras: Vec<&ParagraphNode> = doc.paragraphs.iter().filter(|x| x.section_id == 1).collect();
        assert_eq!(sec1_paras.len(), 2, "两段正文: {:?}", sec1_paras.iter().map(|x| &x.text).collect::<Vec<_>>());
        assert!(sec1_paras[0].text.contains("第一段第一行。\n第一段第二行。"));
        // 全文绝对偏移：第二段起点必须大于第一段终点（跨段落单调）
        assert!(sec1_paras[1].char_offset_start > sec1_paras[0].char_offset_end);
        // 跨章节也保持全文单调
        let sec2: Vec<&ParagraphNode> = doc.paragraphs.iter().filter(|x| x.section_id == 2).collect();
        assert!(sec2[0].char_offset_start > sec1_paras[1].char_offset_end);
    }

    #[test]
    fn sentences_split_on_cjk_and_ascii_terminators() {
        let sents = split_sentences("第一句在这里。第二句！Third one. 第四句；不算新句。3.14 不是断点。");
        let texts: Vec<&str> = sents.iter().map(|(t, _)| t.as_str()).collect();
        assert_eq!(texts.len(), 5, "应切出五句（分号不断句）: {:?}", texts);
        assert_eq!(texts[0], "第一句在这里。");
        assert_eq!(texts[2], "Third one.");
        assert_eq!(texts[3], "第四句；不算新句。");
        assert_eq!(texts[4], "3.14 不是断点。", "小数点不得断句");
    }

    #[test]
    fn markdown_splits_on_h1_and_real_hash() {
        let p = write_tmp(
            "split_check.md",
            "# 甲章\n甲的正文一。\n\n甲的正文二。\n\n# 乙章\n乙的正文。\n",
        );
        let doc = parse_markdown(&p).unwrap();
        assert_eq!(doc.sections.len(), 2);
        assert_eq!(doc.sections[0].title, "甲章");
        assert_eq!(doc.sections[1].title, "乙章");
        assert_eq!(doc.meta.file_hash.len(), 64, "必须是真实 SHA-256 十六进制");
        assert!(!doc.meta.file_hash.contains(|c: char| !c.is_ascii_hexdigit()));
        let first_section = doc.paragraphs[0].section_id;
        let group: Vec<i32> = doc
            .paragraphs
            .iter()
            .filter(|s| s.section_id == first_section)
            .map(|s| s.char_offset_start)
            .collect();
        assert!(group.len() >= 2, "首章节应含多个段落（空行分块）: {:?}", group);
        assert!(group.windows(2).all(|w| w[1] > w[0]), "组内偏移应严格递增: {:?}", group);
    }

    #[test]
    fn unreadable_text_file_errors_instead_of_sample() {
        // 二进制非 UTF-8 内容：read_to_string 必须报错，禁止静默返回示例正文
        let dir = std::env::temp_dir().join(format!("ai_reader_parser_{}", std::process::id()));
        let p = dir.join("binary.txt");
        fs::write(&p, [0xff, 0xfe, 0x00, 0x01]).unwrap();
        assert!(parse_txt(&p.to_string_lossy()).is_err());
    }

    #[test]
    fn txt_single_section_with_paragraphs() {
        let p = write_tmp("plain.txt", "段落一。\n\n段落二。\n");
        let doc = parse_txt(&p).unwrap();
        assert_eq!(doc.sections.len(), 1);
        assert_eq!(doc.sections[0].title, "正文");
        assert_eq!(doc.paragraphs.len(), 2);
    }
}
