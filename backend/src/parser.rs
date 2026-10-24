// backend/src/parser.rs
// 全格式统一文档解构适配器 (Markdown / TXT)
//
// MVP 冻结范围（ai_reader_phased_plan.md CEO Cut C5）：仅 Markdown + TXT。
// PDF / EPUB 显式拒绝并返回明确错误，禁止返回任何占位正文——
// 此前此处以硬编码假论文/假章节"成功"入库，掩盖了格式缺口。

use std::fs;
use std::path::Path;
use sha2::{Digest, Sha256};
use crate::domain::{BookMeta, BookSection, SentenceNode};

#[derive(Debug)]
pub struct ParsedDocument {
    pub meta: BookMeta,
    pub sections: Vec<BookSection>,
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

fn estimate_pages(content: &str) -> i32 {
    // 版心按每页约 1500 字估算；MD/TXT 无物理分页，仅作展示参考值
    (((content.chars().count() as i32) + 1499) / 1500).max(1)
}

/// 按空行行序构建句子切片，char_offset 为章节内真实字符偏移（+1 计换行）
fn build_line_sentences(content: &str, section_pos: i64, page_number: i32) -> Vec<SentenceNode> {
    let mut sentences = Vec::new();
    let mut offset = 0i32;
    for (idx, line) in content.lines().enumerate() {
        let len = line.chars().count() as i32;
        if !line.trim().is_empty() {
            sentences.push(SentenceNode {
                id: 0,
                created_at: String::new(),
                updated_at: String::new(),
                description: None,
                is_del: 0,
                version: 1,
                book_id: 0,
                // 1-based 章节序号占位，由 service.doc_parse 回填真实章节 id
                section_id: section_pos,
                sentence_index: (idx + 1) as i32,
                text: line.trim().to_string(),
                page_number,
                char_offset_start: offset,
                char_offset_end: offset + len,
            });
        }
        offset += len + 1;
    }
    sentences
}

/// 按一级 ATX 标题（`# `）切分 Markdown 章节；无标题时整篇单节
fn split_markdown_sections(content: &str) -> Vec<(String, String)> {
    let mut sections: Vec<(String, String)> = Vec::new();
    let mut current_title = String::new();
    let mut current_body = String::new();
    for line in content.lines() {
        if line.trim_start().starts_with("# ") {
            if !current_title.is_empty() || !current_body.trim().is_empty() {
                sections.push((current_title, current_body));
            }
            current_title = line.trim_start_matches('#').trim().to_string();
            current_body = String::new();
        } else {
            current_body.push_str(line);
            current_body.push('\n');
        }
    }
    if !current_title.is_empty() || !current_body.trim().is_empty() {
        sections.push((current_title, current_body));
    }
    if sections.is_empty() {
        sections.push(("正文".to_string(), content.to_string()));
    }
    sections
}

pub fn parse_markdown(file_path: &str) -> Result<ParsedDocument, String> {
    let content = fs::read_to_string(file_path)
        .map_err(|e| format!("无法读取 Markdown 文件 {}: {}", file_path, e))?;
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
    };

    let mut sections = Vec::new();
    let mut sentences = Vec::new();
    for (idx, (sec_title, body)) in split_markdown_sections(&content).into_iter().enumerate() {
        let section_pos = (idx + 1) as i64;
        let title = if sec_title.is_empty() { "正文".to_string() } else { sec_title };
        sections.push(BookSection {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            book_id: 0,
            section_index: section_pos as i32,
            title,
            parent_id: None,
            start_page: 1,
            end_page: total_pages,
            content: Some(body.clone()),
        });
        sentences.extend(build_line_sentences(&body, section_pos, 1));
    }

    Ok(ParsedDocument { meta, sections, sentences })
}

pub fn parse_txt(file_path: &str) -> Result<ParsedDocument, String> {
    let content = fs::read_to_string(file_path)
        .map_err(|e| format!("无法读取文本文件 {}: {}", file_path, e))?;
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
    };

    let sections = vec![BookSection {
        id: 0,
        created_at: String::new(),
        updated_at: String::new(),
        description: None,
        is_del: 0,
        version: 1,
        book_id: 0,
        section_index: 1,
        title: "正文".to_string(),
        parent_id: None,
        start_page: 1,
        end_page: total_pages,
        content: Some(content.clone()),
    }];
    let sentences = build_line_sentences(&content, 1, 1);

    Ok(ParsedDocument { meta, sections, sentences })
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
    fn markdown_splits_on_h1_and_real_hash() {
        let p = write_tmp(
            "split_check.md",
            "# 甲章\n甲的正文一。\n甲的正文二。\n\n# 乙章\n乙的正文。\n",
        );
        let doc = parse_markdown(&p).unwrap();
        assert_eq!(doc.sections.len(), 2);
        assert_eq!(doc.sections[0].title, "甲章");
        assert_eq!(doc.sections[1].title, "乙章");
        assert_eq!(doc.meta.file_hash.len(), 64, "必须是真实 SHA-256 十六进制");
        assert!(!doc.meta.file_hash.contains(|c: char| !c.is_ascii_hexdigit()));
        // 偏移按章节内真实字符位置累计（局部坐标），组内须单调递增且非固定步长
        let first_section = doc.sentences[0].section_id;
        let group: Vec<i32> = doc
            .sentences
            .iter()
            .filter(|s| s.section_id == first_section)
            .map(|s| s.char_offset_start)
            .collect();
        assert!(group.len() >= 2, "首章节应含多句: {:?}", group);
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
}
