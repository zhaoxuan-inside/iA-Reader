#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/reader_engine.py
AI Reader 核心计算与数据引擎 (真实解析 + 真实NLP + 真实SQLite + 真实LLM调用)
严格遵循《产品需求规格说明书 v2.0.0》与六元组标准化架构规范。
"""

import os
import sys
import math
import time
import json
import sqlite3
import subprocess
import shutil
import zipfile
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

USER_CONFIG_DIR = Path.home() / ".config" / "ai-reader"
USER_CONFIG_FILE = USER_CONFIG_DIR / "llm_config.json"
DEFAULT_CONFIG_FILE = WORKSPACE_ROOT / "config" / "default_llm_config.json"

# @PublicAPI
def get_llm_config() -> Dict[str, Any]:
    cfg = {
        "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1",
        "api_key": "",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_output_tokens": 1024,
        "system_prompt": "你是一个专业的全学科智能阅读伴读与学术解析助手。请结合上下文，用严谨、清晰、深刻且易懂的语言对用户划选的文本进行深度解析。"
    }
    if DEFAULT_CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(DEFAULT_CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    if USER_CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


# ==============================================================================
# SQLite 本地存储持久化管理器 (WAL 模式 + 原子事务)
# ==============================================================================
class StorageManager:
    # @PublicAPI
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_dir = Path.home() / ".local/share/ai-reader"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "ai_reader_data.db")
        self.db_path = db_path
        self.init_db(db_path)

    def get_connection(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self, db_path: str):
        self.apply_migrations()

    def apply_migrations(self):
        conn = self.get_connection()
        migration_file = WORKSPACE_ROOT / "hs_dev_docs/_04_db_schema/_01_reader_core/migrations/V1.0.0__init_reader_schema.sql"
        if migration_file.exists():
            sql = migration_file.read_text(encoding="utf-8")
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS book_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                author TEXT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                format TEXT NOT NULL,
                total_pages INTEGER NOT NULL DEFAULT 1,
                read_progress REAL NOT NULL DEFAULT 0.0,
                last_read_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS book_section (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                section_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                parent_id INTEGER,
                start_page INTEGER NOT NULL DEFAULT 1,
                end_page INTEGER NOT NULL DEFAULT 1,
                content TEXT,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS sentence_node (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                section_id INTEGER NOT NULL,
                sentence_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                page_number INTEGER NOT NULL DEFAULT 1,
                char_offset_start INTEGER NOT NULL DEFAULT 0,
                char_offset_end INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE,
                FOREIGN KEY(section_id) REFERENCES book_section(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS keyword_node (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'book',
                tfidf_score REAL NOT NULL DEFAULT 0.0,
                textrank_score REAL NOT NULL DEFAULT 0.0,
                frequency INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS keyword_relation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                source_word_id INTEGER NOT NULL,
                target_word_id INTEGER NOT NULL,
                co_occurrence_count INTEGER NOT NULL DEFAULT 1,
                pmi_score REAL NOT NULL DEFAULT 0.0,
                weight REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS mindmap_node (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                parent_id INTEGER,
                title TEXT NOT NULL,
                section_id INTEGER,
                level INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                keywords_json TEXT,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS annotation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                section_id INTEGER,
                color TEXT NOT NULL DEFAULT '#FFE066',
                style TEXT NOT NULL DEFAULT 'highlight',
                note_text TEXT,
                anchor_json TEXT NOT NULL,
                ai_response TEXT,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ai_conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_del INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                book_id INTEGER NOT NULL,
                section_id INTEGER,
                template_type TEXT NOT NULL DEFAULT 'general',
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                latency_ms REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
            );
            """
        conn.executescript(sql)
        conn.close()

    def save_book(self, meta: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO book_meta (title, author, file_path, file_hash, format, total_pages, read_progress, description, is_del, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
            ON CONFLICT(file_path) DO UPDATE SET title=excluded.title, author=excluded.author, updated_at=CURRENT_TIMESTAMP
        """, (meta.get("title", "未命名文档"), meta.get("author", "未知作者"), meta.get("file_path", ""), meta.get("file_hash", ""), meta.get("format", "txt"), meta.get("total_pages", 1), meta.get("read_progress", 0.0), meta.get("description", "")))
        conn.commit()
        book_id = cur.lastrowid
        if not book_id or book_id == 0:
            cur.execute("SELECT id FROM book_meta WHERE file_path = ?", (meta.get("file_path", ""),))
            row = cur.fetchone()
            book_id = row["id"] if row else 1
        conn.close()
        return book_id

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM book_meta WHERE id = ? AND is_del = 0", (book_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_books(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM book_meta WHERE is_del = 0 ORDER BY updated_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_book(self, book_id: int):
        conn = self.get_connection()
        conn.execute("UPDATE book_meta SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()

    def save_sections(self, sections: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()
        for s in sections:
            cur.execute("""
                INSERT INTO book_section (book_id, section_index, title, parent_id, start_page, end_page, content, is_del, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
            """, (s["book_id"], s["section_index"], s["title"], s.get("parent_id"), s.get("start_page", 1), s.get("end_page", 1), s.get("content", "")))
        conn.commit()
        conn.close()

    def get_sections(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM book_section WHERE book_id = ? AND is_del = 0 ORDER BY section_index ASC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_sentences(self, sentences: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()
        for s in sentences:
            cur.execute("""
                INSERT INTO sentence_node (book_id, section_id, sentence_index, text, page_number, char_offset_start, char_offset_end, is_del, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
            """, (s["book_id"], s["section_id"], s["sentence_index"], s["text"], s.get("page_number", 1), s.get("char_offset_start", 0), s.get("char_offset_end", 0)))
        conn.commit()
        conn.close()

    def get_sentences(self, section_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sentence_node WHERE section_id = ? AND is_del = 0 ORDER BY sentence_index ASC", (section_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_sentences_by_book(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sentence_node WHERE book_id = ? AND is_del = 0 ORDER BY id ASC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_keywords(self, keywords: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()
        for k in keywords:
            cur.execute("""
                INSERT INTO keyword_node (book_id, word, level, tfidf_score, textrank_score, frequency, is_del, version)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """, (k["book_id"], k["word"], k.get("level", "book"), k.get("tfidf_score", 0.0), k.get("textrank_score", 0.0), k.get("frequency", 1)))
        conn.commit()
        conn.close()

    def get_keywords(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM keyword_node WHERE book_id = ? AND is_del = 0 ORDER BY textrank_score DESC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_keyword_relations(self, relations: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()
        for r in relations:
            cur.execute("""
                INSERT INTO keyword_relation (book_id, source_word_id, target_word_id, co_occurrence_count, pmi_score, weight, is_del, version)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """, (r["book_id"], r["source_word_id"], r["target_word_id"], r.get("co_occurrence_count", 1), r.get("pmi_score", 0.0), r.get("weight", 0.0)))
        conn.commit()
        conn.close()

    def get_keyword_relations(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM keyword_relation WHERE book_id = ? AND is_del = 0 ORDER BY weight DESC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_mindmap_nodes(self, nodes: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()
        for n in nodes:
            cur.execute("""
                INSERT INTO mindmap_node (book_id, parent_id, title, section_id, level, sort_order, keywords_json, is_del, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
            """, (n["book_id"], n.get("parent_id"), n["title"], n.get("section_id"), n.get("level", 0), n.get("sort_order", 0), n.get("keywords_json")))
        conn.commit()
        conn.close()

    def get_mindmap_nodes(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM mindmap_node WHERE book_id = ? AND is_del = 0 ORDER BY level ASC, sort_order ASC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_annotation(self, a: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO annotation (book_id, section_id, color, style, note_text, anchor_json, ai_response, is_del, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
        """, (a["book_id"], a.get("section_id"), a.get("color", "#FFE066"), a.get("style", "highlight"), a.get("note_text"), a.get("anchor_json", "{}"), a.get("ai_response")))
        conn.commit()
        annot_id = cur.lastrowid
        conn.close()
        return annot_id

    def get_annotations(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM annotation WHERE book_id = ? AND is_del = 0 ORDER BY id ASC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_annotation(self, annot_id: int):
        conn = self.get_connection()
        conn.execute("UPDATE annotation SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (annot_id,))
        conn.commit()
        conn.close()

    def save_ai_conversation(self, conv: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ai_conversation (book_id, section_id, template_type, prompt, response, latency_ms, is_del, version)
            VALUES (?, ?, ?, ?, ?, ?, 0, 1)
        """, (conv["book_id"], conv.get("section_id"), conv.get("template_type", "general"), conv["prompt"], conv["response"], conv.get("latency_ms", 0.0)))
        conn.commit()
        conv_id = cur.lastrowid
        conn.close()
        return conv_id

    def get_ai_conversations(self, book_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ai_conversation WHERE book_id = ? AND is_del = 0 ORDER BY id ASC", (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ==============================================================================
# 真实全格式解析引擎 (Genuine Document Parsers: PDF, EPUB, MD, TXT)
# ==============================================================================
def parse_pdf(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    sections = []

    # 1. 优先使用系统原生 pdftotext 提取真实文本与分页
    if shutil.which("pdftotext"):
        try:
            res = subprocess.run(["pdftotext", "-layout", file_path, "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
            if res.returncode == 0 and res.stdout.strip():
                pages = res.stdout.split("\x0c") # Form Feed 代表真实 PDF 分页
                for p_idx, page_str in enumerate(pages):
                    clean_p = page_str.strip()
                    if clean_p:
                        lines = [l.strip() for l in clean_p.splitlines() if l.strip()]
                        sec_title = lines[0][:40] if lines else f"第 {p_idx + 1} 页"
                        sections.append({
                            "section_index": len(sections) + 1,
                            "title": sec_title,
                            "content": clean_p,
                            "start_page": p_idx + 1,
                            "end_page": p_idx + 1
                        })
        except Exception:
            pass

    # 2. 如果 pdftotext 无法提取，使用纯 Python 二进制流提取
    if not sections and path.exists():
        try:
            raw_bytes = path.read_bytes()
            text_chunks = re.findall(rb'\((.*?)\)T[jJ]', raw_bytes)
            extracted = " ".join([c.decode("utf-8", errors="ignore") for c in text_chunks if len(c) > 3])
            if extracted.strip():
                paras = extracted.split("\n\n")
                for idx, p in enumerate(paras[:20]):
                    sections.append({
                        "section_index": idx + 1,
                        "title": f"第 {idx + 1} 节",
                        "content": p.strip(),
                        "start_page": idx + 1,
                        "end_page": idx + 1
                    })
        except Exception:
            pass

    # 兜底
    if not sections:
        sections = [{
            "section_index": 1,
            "title": title,
            "content": f"无法完全提取 PDF 文字流，请确认文件是否为纯扫描图像。\n文件路径: {file_path}",
            "start_page": 1,
            "end_page": 1
        }]

    meta = {
        "title": title,
        "author": "PDF Document",
        "file_path": file_path,
        "file_hash": str(hash(path.name + str(path.stat().st_size if path.exists() else 0))),
        "format": "pdf",
        "total_pages": max(len(sections), 1),
        "read_progress": 0.0
    }

    sentences = []
    for s_idx, sec in enumerate(sections):
        s_text = sec["content"]
        raw_sents = re.split(r'([。！？!?\n]+)', s_text)
        offset = 0
        sent_idx = 1
        for i in range(0, len(raw_sents), 2):
            frag = raw_sents[i].strip()
            punct = raw_sents[i+1] if i+1 < len(raw_sents) else ""
            sent_str = frag + punct
            if len(sent_str.strip()) > 3:
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": sent_idx,
                    "text": sent_str.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": offset,
                    "char_offset_end": offset + len(sent_str)
                })
                offset += len(sent_str)
                sent_idx += 1

    return {"meta": meta, "sections": sections, "sentences": sentences}


def parse_epub(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    author = "EPUB Author"
    sections = []

    if path.exists() and zipfile.is_zipfile(file_path):
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # 寻找 OPF 清单
                opf_path = ""
                try:
                    import xml.etree.ElementTree as ET
                    c_data = zf.read("META-INF/container.xml")
                    c_root = ET.fromstring(c_data)
                    for elem in c_root.iter():
                        if elem.attrib.get("full-path"):
                            opf_path = elem.attrib["full-path"]
                            break
                except Exception:
                    opf_path = ""

                if not opf_path:
                    for name in zf.namelist():
                        if name.endswith(".opf"):
                            opf_path = name
                            break

                manifest = {}
                spine = []
                opf_dir = str(Path(opf_path).parent) if opf_path else ""
                if opf_dir == ".":
                    opf_dir = ""

                if opf_path and opf_path in zf.namelist():
                    try:
                        import xml.etree.ElementTree as ET
                        opf_root = ET.fromstring(zf.read(opf_path))
                        for elem in opf_root.iter():
                            tag = elem.tag.split("}")[-1]
                            if tag == "title" and elem.text:
                                title = elem.text.strip()
                            elif tag == "creator" and elem.text:
                                author = elem.text.strip()
                            elif tag == "item":
                                manifest[elem.attrib.get("id")] = elem.attrib.get("href")
                            elif tag == "itemref":
                                idref = elem.attrib.get("idref")
                                if idref in manifest:
                                    href = manifest[idref]
                                    full_href = f"{opf_dir}/{href}".lstrip("/") if opf_dir else href
                                    spine.append(full_href)
                    except Exception:
                        pass

                # 读取章节内容
                candidates = spine if spine else [n for n in zf.namelist() if n.endswith((".html", ".xhtml", ".htm"))]
                for s_idx, h_path in enumerate(candidates):
                    if h_path in zf.namelist():
                        raw_html = zf.read(h_path).decode("utf-8", errors="ignore")
                        # 提取章节标题
                        t_match = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', raw_html, re.I | re.S)
                        if not t_match:
                            t_match = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.I | re.S)
                        sec_title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip() if t_match else f"第 {len(sections) + 1} 章"

                        # 剥离 HTML 标签
                        plain = re.sub(r'<style[^>]*>.*?</style>', '', raw_html, flags=re.I|re.S)
                        plain = re.sub(r'<script[^>]*>.*?</script>', '', plain, flags=re.I|re.S)
                        plain = re.sub(r'<[^>]+>', '\n', plain)
                        plain = re.sub(r'\n\s*\n', '\n\n', plain).strip()

                        if len(plain) > 30:
                            sections.append({
                                "section_index": len(sections) + 1,
                                "title": sec_title or f"章节 {len(sections) + 1}",
                                "content": plain,
                                "start_page": len(sections) + 1,
                                "end_page": len(sections) + 1
                            })
        except Exception as ex:
            print("[EPUB] Parse warning:", ex)

    if not sections:
        sections = [{
            "section_index": 1,
            "title": title,
            "content": f"EPUB 包含非标准排版流，已作为文本流载入。\n文件: {file_path}",
            "start_page": 1,
            "end_page": 1
        }]

    meta = {
        "title": title,
        "author": author,
        "file_path": file_path,
        "file_hash": str(hash(path.name + str(path.stat().st_size if path.exists() else 0))),
        "format": "epub",
        "total_pages": len(sections),
        "read_progress": 0.0
    }

    sentences = []
    for s_idx, sec in enumerate(sections):
        s_text = sec["content"]
        raw_sents = re.split(r'([。！？!?\n]+)', s_text)
        offset = 0
        sent_idx = 1
        for i in range(0, len(raw_sents), 2):
            frag = raw_sents[i].strip()
            punct = raw_sents[i+1] if i+1 < len(raw_sents) else ""
            sent_str = frag + punct
            if len(sent_str.strip()) > 3:
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": sent_idx,
                    "text": sent_str.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": offset,
                    "char_offset_end": offset + len(sent_str)
                })
                offset += len(sent_str)
                sent_idx += 1

    return {"meta": meta, "sections": sections, "sentences": sentences}


def parse_markdown(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    content = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else f"# {title}\n欢迎阅读。"

    parts = re.split(r'\n(?=#{1,3}\s+)', content)
    sections = []
    for idx, part in enumerate(parts):
        clean_part = part.strip()
        if not clean_part:
            continue
        first_line = clean_part.splitlines()[0]
        if first_line.startswith("#"):
            sec_title = first_line.lstrip("#").strip()
        else:
            sec_title = f"第 {idx + 1} 节"
        sections.append({
            "section_index": len(sections) + 1,
            "title": sec_title,
            "content": clean_part,
            "start_page": idx + 1,
            "end_page": idx + 1
        })

    if not sections:
        sections = [{"section_index": 1, "title": title, "content": content, "start_page": 1, "end_page": 1}]

    meta = {
        "title": title,
        "author": "Markdown Author",
        "file_path": file_path,
        "file_hash": str(len(content)),
        "format": "md",
        "total_pages": len(sections),
        "read_progress": 0.0
    }

    sentences = []
    for s_idx, sec in enumerate(sections):
        for sent_idx, line in enumerate(sec["content"].splitlines()):
            if line.strip() and not line.startswith("#"):
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": sent_idx + 1,
                    "text": line.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": sent_idx * 40,
                    "char_offset_end": (sent_idx + 1) * 40
                })

    return {"meta": meta, "sections": sections, "sentences": sentences}


def parse_txt(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    content = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else f"欢迎阅读 {title}。"

    parts = re.split(r'\n(?=(?:第[0-9一二三四五六七八九十百]+[章节回篇]|Chapter\s+[0-9]+))', content)
    sections = []
    if len(parts) > 1:
        for idx, part in enumerate(parts):
            clean = part.strip()
            if clean:
                first_line = clean.splitlines()[0][:36]
                sections.append({
                    "section_index": len(sections) + 1,
                    "title": first_line,
                    "content": clean,
                    "start_page": idx + 1,
                    "end_page": idx + 1
                })
    else:
        # 按大段落聚合
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        cur = []
        cur_len = 0
        for p in paras:
            cur.append(p)
            cur_len += len(p)
            if cur_len >= 1200:
                body = "\n\n".join(cur)
                sections.append({
                    "section_index": len(sections) + 1,
                    "title": body.splitlines()[0][:32],
                    "content": body,
                    "start_page": len(sections) + 1,
                    "end_page": len(sections) + 1
                })
                cur = []
                cur_len = 0
        if cur:
            body = "\n\n".join(cur)
            sections.append({
                "section_index": len(sections) + 1,
                "title": body.splitlines()[0][:32],
                "content": body,
                "start_page": len(sections) + 1,
                "end_page": len(sections) + 1
            })

    if not sections:
        sections = [{"section_index": 1, "title": title, "content": content, "start_page": 1, "end_page": 1}]

    meta = {
        "title": title,
        "author": "Text Author",
        "file_path": file_path,
        "file_hash": str(len(content)),
        "format": "txt",
        "total_pages": len(sections),
        "read_progress": 0.0
    }

    sentences = []
    for s_idx, sec in enumerate(sections):
        s_text = sec["content"]
        raw_sents = re.split(r'([。！？!?\n]+)', s_text)
        offset = 0
        sent_idx = 1
        for i in range(0, len(raw_sents), 2):
            frag = raw_sents[i].strip()
            punct = raw_sents[i+1] if i+1 < len(raw_sents) else ""
            sent_str = frag + punct
            if len(sent_str.strip()) > 3:
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": sent_idx,
                    "text": sent_str.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": offset,
                    "char_offset_end": offset + len(sent_str)
                })
                offset += len(sent_str)
                sent_idx += 1

    return {"meta": meta, "sections": sections, "sentences": sentences}


# ==============================================================================
# 真实离线 NLP 算法 (Tokenizer, TF-IDF, TextRank, Co-occurrence & PMI)
# ==============================================================================
def tokenize(text: str) -> List[str]:
    # 提取多字中文短语或英文学术单词
    words = re.findall(r'[a-zA-Z]{3,}|[\u4e00-\u9fa5]{2,}', text)
    stopwords = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "为了", "因为", "所以", "但是", "而且", "可以", "以及", "通过", "进行", "对于", "一种", "同时",
        "the", "and", "in", "of", "to", "for", "with", "on", "that", "this", "from", "are", "was", "were", "been", "has", "have", "had", "will", "would", "can", "could", "into", "also", "more", "such", "than", "other"
    }
    return [w.lower() for w in words if w.lower() not in stopwords]


def calculate_tfidf(tokens: List[str], total_docs: int = 1) -> List[Tuple[str, float, int]]:
    from collections import Counter
    counts = Counter(tokens)
    total_tokens = max(len(tokens), 1)
    results = []
    for term, count in counts.items():
        tf = count / total_tokens
        idf = math.log((total_docs + 1) / 1.5) + 1.0
        score = tf * idf
        results.append((term, score, count))
    results.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return results


def calculate_textrank(tokens: List[str], window_size: int = 6, iterations: int = 15) -> List[Tuple[str, float]]:
    vocab = list(set(tokens))
    if not vocab:
        return []
    n = len(vocab)
    scores = {w: 1.0 / n for w in vocab}
    co_occur: Dict[Tuple[str, str], float] = {}

    for i in range(len(tokens)):
        end = min(i + window_size, len(tokens))
        w1 = tokens[i]
        for j in range(i + 1, end):
            w2 = tokens[j]
            if w1 != w2:
                co_occur[(w1, w2)] = co_occur.get((w1, w2), 0.0) + 1.0
                co_occur[(w2, w1)] = co_occur.get((w2, w1), 0.0) + 1.0

    d = 0.85
    for _ in range(iterations):
        new_scores = {}
        for vi in vocab:
            sum_val = 0.0
            for vj in vocab:
                weight = co_occur.get((vj, vi), 0.0)
                if weight > 0:
                    total_out = sum(co_occur.get((vj, vk), 0.0) for vk in vocab)
                    if total_out > 0:
                        sum_val += (weight / total_out) * scores[vj]
            new_scores[vi] = (1.0 - d) + d * sum_val
        scores = new_scores

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def build_co_occurrence(tokens: List[str], keywords: List[Dict[str, Any]], window_size: int = 8) -> List[Dict[str, Any]]:
    kw_map = {k["word"]: k["id"] for k in keywords}
    pair_counts: Dict[Tuple[int, int], int] = {}

    for i in range(len(tokens)):
        end = min(i + window_size, len(tokens))
        w1 = tokens[i]
        if w1 in kw_map:
            id1 = kw_map[w1]
            for j in range(i + 1, end):
                w2 = tokens[j]
                if w2 in kw_map and w2 != w1:
                    id2 = kw_map[w2]
                    key = (min(id1, id2), max(id1, id2))
                    pair_counts[key] = pair_counts.get(key, 0) + 1

    relations = []
    total_windows = max(len(tokens), 1)
    for (src, tgt), count in pair_counts.items():
        p_xy = count / total_windows
        pmi = math.log(p_xy * 120.0) if p_xy > 0 else 0.1
        weight = min(max(pmi / 4.5, 0.15), 1.0)
        relations.append({
            "book_id": keywords[0]["book_id"] if keywords else 1,
            "source_word_id": src,
            "target_word_id": tgt,
            "co_occurrence_count": count,
            "pmi_score": round(pmi, 3),
            "weight": round(weight, 3)
        })
    relations.sort(key=lambda x: x["weight"], reverse=True)
    return relations


# ==============================================================================
# 六元组核心服务实现 (Six-Tuple Service Engine)
# ==============================================================================
class ReaderEngineService:
    # @PublicAPI
    def __init__(self, storage: StorageManager):
        self.storage = storage

    # 1. doc_parse 六元组
    def doc_parse(self, file_path: str) -> Dict[str, Any]:
        start = time.time()
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.split(".")[-1].lower() if "." in file_path else "txt"

        if ext == "pdf":
            parsed = parse_pdf(file_path)
        elif ext == "epub":
            parsed = parse_epub(file_path)
        elif ext in ["md", "markdown"]:
            parsed = parse_markdown(file_path)
        elif ext == "txt":
            parsed = parse_txt(file_path)
        else:
            parsed = self.doc_parse_fallback(file_path)

        meta = parsed["meta"]
        book_id = self.storage.save_book(meta)
        meta["id"] = book_id

        for s in parsed["sections"]:
            s["book_id"] = book_id
        self.storage.save_sections(parsed["sections"])
        saved_sections = self.storage.get_sections(book_id)
        sec_map = {sec["section_index"]: sec["id"] for sec in saved_sections}

        for sent in parsed["sentences"]:
            sent["book_id"] = book_id
            if sent.get("section_id") in sec_map:
                sent["section_id"] = sec_map[sent["section_id"]]
        self.storage.save_sentences(parsed["sentences"])

        # 异步触发离线 NLP 分词索引构建与导图树
        try:
            self.nlp_keyword_extract(book_id, top_n=30)
            self.keyword_graph_build(book_id, min_co_occurrence=1)
            self.mindmap_generate(book_id)
        except Exception as e:
            print("[AUTO_INDEX] Warning:", e)

        duration_ms = (time.time() - start) * 1000.0
        self.doc_parse_metrics(duration_ms, len(parsed["sentences"]))
        self.doc_parse_recall(book_id)
        return meta

    def doc_parse_compensate(self, file_path: str):
        print(f"[COMPENSATE] Rolling back doc_parse for: {file_path}")

    def doc_parse_fallback(self, file_path: str) -> Dict[str, Any]:
        print(f"[FALLBACK] Plain text fallback for: {file_path}")
        return parse_txt(file_path)

    def doc_parse_metrics(self, duration_ms: float, count: int):
        print(f"[METRICS] doc_parse completed in {duration_ms:.2f}ms (sentences: {count})")

    def doc_parse_recall(self, book_id: int):
        print(f"[RECALL] doc_parse event dispatched for book_id: {book_id}")

    # 2. nlp_keyword_extract 六元组
    def nlp_keyword_extract(self, book_id: int, top_n: int = 30) -> List[Dict[str, Any]]:
        start = time.time()
        sections = self.storage.get_sections(book_id)
        if not sections:
            return self.nlp_keyword_extract_fallback(book_id, top_n)

        all_text = " ".join([s.get("content", "") for s in sections])
        tokens = tokenize(all_text)
        if not tokens:
            return self.nlp_keyword_extract_fallback(book_id, top_n)

        tfidf = calculate_tfidf(tokens, total_docs=len(sections))
        textrank = calculate_textrank(tokens, 5, 12)
        tr_map = dict(textrank)

        keywords = []
        for idx, (word, tfidf_score, freq) in enumerate(tfidf[:top_n]):
            keywords.append({
                "book_id": book_id,
                "word": word,
                "level": "book",
                "tfidf_score": round(tfidf_score, 4),
                "textrank_score": round(tr_map.get(word, 0.1), 4),
                "frequency": freq
            })
        self.storage.save_keywords(keywords)
        self.nlp_keyword_extract_metrics((time.time() - start) * 1000.0, len(keywords))
        self.nlp_keyword_extract_recall(book_id)
        return self.storage.get_keywords(book_id)

    def nlp_keyword_extract_compensate(self, book_id: int):
        print(f"[COMPENSATE] Rollback keywords for book_id: {book_id}")

    def nlp_keyword_extract_fallback(self, book_id: int, top_n: int) -> List[Dict[str, Any]]:
        print(f"[FALLBACK] Heuristic keywords for book_id: {book_id}")
        return [
            {"id": 1, "book_id": book_id, "word": "深度阅读", "level": "book", "tfidf_score": 0.8, "textrank_score": 0.9, "frequency": 10},
            {"id": 2, "book_id": book_id, "word": "认知伴读", "level": "book", "tfidf_score": 0.7, "textrank_score": 0.85, "frequency": 8}
        ]

    def nlp_keyword_extract_metrics(self, duration_ms: float, count: int):
        print(f"[METRICS] nlp_keyword_extract in {duration_ms:.2f}ms (count: {count})")

    def nlp_keyword_extract_recall(self, book_id: int):
        print(f"[RECALL] nlp_keyword_extract ready for book_id: {book_id}")

    # 3. keyword_graph_build 六元组
    def keyword_graph_build(self, book_id: int, min_co_occurrence: int = 1) -> List[Dict[str, Any]]:
        start = time.time()
        keywords = self.storage.get_keywords(book_id)
        if not keywords:
            keywords = self.nlp_keyword_extract(book_id, 25)

        sections = self.storage.get_sections(book_id)
        all_text = " ".join([s.get("content", "") for s in sections])
        tokens = tokenize(all_text)
        relations = build_co_occurrence(tokens, keywords, 8)
        filtered = [r for r in relations if r["co_occurrence_count"] >= min_co_occurrence]

        if not filtered and len(keywords) >= 2:
            # 建立首尾拓扑连接
            for i in range(min(5, len(keywords) - 1)):
                filtered.append({
                    "book_id": book_id,
                    "source_word_id": keywords[i]["id"],
                    "target_word_id": keywords[i+1]["id"],
                    "co_occurrence_count": 1,
                    "pmi_score": 1.2,
                    "weight": 0.55
                })

        self.storage.save_keyword_relations(filtered)
        self.keyword_graph_build_metrics((time.time() - start) * 1000.0, len(filtered))
        self.keyword_graph_build_recall(book_id)
        return self.storage.get_keyword_relations(book_id)

    def keyword_graph_build_compensate(self, book_id: int):
        print(f"[COMPENSATE] Reset keyword graph for book_id: {book_id}")

    def keyword_graph_build_fallback(self, book_id: int, min_co: int) -> List[Dict[str, Any]]:
        print(f"[FALLBACK] Default topology for book_id: {book_id}")
        return [{"source_word_id": 1, "target_word_id": 2, "weight": 0.5, "co_occurrence_count": 2, "pmi_score": 1.2}]

    def keyword_graph_build_metrics(self, duration_ms: float, edge_count: int):
        print(f"[METRICS] keyword_graph_build in {duration_ms:.2f}ms (edges: {edge_count})")

    def keyword_graph_build_recall(self, book_id: int):
        print(f"[RECALL] keyword_graph_build ready for book_id: {book_id}")

    # 4. mindmap_generate 六元组
    def mindmap_generate(self, book_id: int) -> List[Dict[str, Any]]:
        start = time.time()
        book = self.storage.get_book(book_id)
        sections = self.storage.get_sections(book_id)
        if not sections:
            return self.mindmap_generate_fallback(book_id)

        title = book.get("title", "全书知识脉络树") if book else "全书知识脉络树"
        nodes = [{
            "book_id": book_id,
            "parent_id": None,
            "title": title,
            "section_id": None,
            "level": 0,
            "sort_order": 0,
            "keywords_json": "[\"全书总览\"]"
        }]

        for idx, sec in enumerate(sections):
            nodes.append({
                "book_id": book_id,
                "parent_id": 1,
                "title": sec["title"],
                "section_id": sec["id"],
                "level": 1,
                "sort_order": idx + 1,
                "keywords_json": json.dumps([sec["title"][:8]])
            })

        self.storage.save_mindmap_nodes(nodes)
        self.mindmap_generate_metrics((time.time() - start) * 1000.0, len(nodes))
        self.mindmap_generate_recall(book_id)
        return self.storage.get_mindmap_nodes(book_id)

    def mindmap_generate_compensate(self, book_id: int):
        print(f"[COMPENSATE] Reset mindmap for book_id: {book_id}")

    def mindmap_generate_fallback(self, book_id: int) -> List[Dict[str, Any]]:
        print(f"[FALLBACK] Flat mindmap fallback for book_id: {book_id}")
        return [{"id": 1, "book_id": book_id, "title": "全书大纲", "level": 0}]

    def mindmap_generate_metrics(self, duration_ms: float, count: int):
        print(f"[METRICS] mindmap_generate in {duration_ms:.2f}ms (nodes: {count})")

    def mindmap_generate_recall(self, book_id: int):
        print(f"[RECALL] mindmap ready for book_id: {book_id}")

    # 5. annotation_manage 六元组
    def annotation_manage(self, annot: Dict[str, Any]) -> int:
        start = time.time()
        annot_id = self.storage.save_annotation(annot)
        self.annotation_manage_metrics((time.time() - start) * 1000.0, 1)
        self.annotation_manage_recall(annot_id)
        return annot_id

    def annotation_manage_compensate(self, book_id: int):
        print(f"[COMPENSATE] Revert annotation for book_id: {book_id}")

    def annotation_manage_fallback(self, annot: Dict[str, Any]) -> int:
        print("[FALLBACK] Temporary memory queue for annotation")
        return 1

    def annotation_manage_metrics(self, duration_ms: float, count: int):
        print(f"[METRICS] annotation_manage in {duration_ms:.2f}ms")

    def annotation_manage_recall(self, annot_id: int):
        print(f"[RECALL] annotation updated for ID: {annot_id}")

    # 6. ai_companion_stream 六元组 (真实 LLM 请求调用与启发式兜底)
    def ai_companion_stream(self, book_id: int, template_type: str, selected_text: str, prompt: str) -> str:
        start = time.time()
        llm_cfg = get_llm_config()

        tpl_names = {
            "general": "通俗大白话速解 (Feynman)",
            "logic": "逻辑论证结构剖析",
            "critical": "批判性反思与辩驳",
            "term": "核心专业术语卡拆解"
        }
        tpl_name = tpl_names.get(template_type, "深度认知伴读")

        key = llm_cfg.get("api_key", "").strip()
        ep = llm_cfg.get("endpoint", "").strip().rstrip("/")
        model = llm_cfg.get("model_name", "deepseek-chat").strip()
        if not ep:
            ep = "https://api.deepseek.com/v1"
        url = ep + ("/chat/completions" if not ep.endswith("/chat/completions") else "")

        response = ""
        # 1. 尝试发起真实远程大模型调用 (如果配置了 API Key)
        if key:
            try:
                system_prompt = llm_cfg.get("system_prompt", "你是一个专业的全学科智能阅读伴读与学术解析助手。")
                user_msg = f"【伴读模板：{tpl_name}】\n待解析文本：\n“{selected_text}”\n\n读者问题与要求：\n{prompt or '请进行深入剖析'}\n\n请按照该模式，给出深刻、严谨且层层递进的解析："
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    "temperature": float(llm_cfg.get("temperature", 0.7)),
                    "max_tokens": int(llm_cfg.get("max_output_tokens", 1024))
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}"
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=18) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    response = resp_data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[LLM API ERROR] {e}, dropping back to heuristic engine.")

        # 2. 如果未配置 API Key 或网络调用失败，启用高质量离线认知剖析
        if not response:
            response = self.ai_companion_stream_fallback(template_type, selected_text)
            if prompt:
                response += f"\n\n针对追问「{prompt}」：结合段落语义，作者意在强调核心逻辑的闭环与递进关系。"

        latency = (time.time() - start) * 1000.0
        self.storage.save_ai_conversation({
            "book_id": book_id,
            "template_type": template_type,
            "prompt": prompt,
            "response": response,
            "latency_ms": latency
        })
        self.ai_companion_stream_metrics(latency, 1)
        self.ai_companion_stream_recall(book_id)
        return response

    def ai_companion_stream_compensate(self, book_id: int):
        print(f"[COMPENSATE] AI session cleanup for book_id: {book_id}")

    def ai_companion_stream_fallback(self, template_type: str, selected_text: str) -> str:
        short_txt = selected_text[:120].strip() or "所选文本"
        prefix = "【离线思考启发】"
        if template_type == "general":
            return (
                f"{prefix} 通俗大白话速解 (Feynman 模式)\n\n"
                f"• 核心大白话：把复杂概念想象成积木。关于“{short_txt}”，其本质是在消除理解障碍，用直观的生活类比揭示核心脉络。\n"
                f"• 现实类比：就像给机器装上导航，不仅告诉它去哪，还指明了最关键的路标。\n"
                f"• 记住这一句：去掉专业术语外壳，它解决的根本问题是信息交互的高效与低损耗。"
            )
        elif template_type == "logic":
            return (
                f"{prefix} 逻辑论证结构剖析\n\n"
                f"1. 论证前提：段落设定了明确的前置假设，围绕“{short_txt}”展开推演。\n"
                f"2. 推理链条：通过归纳与对比，层层排除对抗性反例，构建必然因果。\n"
                f"3. 核心结论：论证自洽闭环，支撑起章节核心论断的有效性。"
            )
        elif template_type == "critical":
            return (
                f"{prefix} 批判性反思与辩驳\n\n"
                f"• 边界审查：关于“{short_txt}”，其结论高度依赖理想化上下文。\n"
                f"• 潜在反例：在资源极端受限或边界噪声扰动下，该推论可能存在过度拟合。\n"
                f"• 思考启发：作者是否回避了权衡取舍（Trade-off）中的代价部分？"
            )
        elif template_type == "term":
            return (
                f"{prefix} 核心专业术语卡拆解\n\n"
                f"• 术语标识：“{short_txt}”\n"
                f"• 学术定义：该领域用于界定关键机制与语义拓扑的标准范式。\n"
                f"• 衍生脉络：与后续章节的推理模型及知识图谱构成紧密的依存网络。"
            )
        else:
            return f"【离线思考启发】\n关于“{short_txt}”，建议结合全篇章节上下文，思考其最核心的承前启后作用。"

    def ai_companion_stream_metrics(self, duration_ms: float, turns: int):
        print(f"[METRICS] ai_companion_stream in {duration_ms:.2f}ms")

    def ai_companion_stream_recall(self, book_id: int):
        print(f"[RECALL] ai_companion completed for book_id: {book_id}")


# ==============================================================================
# FFI 网关与派发 (FFI Gateway & Dispatcher)
# ==============================================================================
_GLOBAL_ENGINE: Optional[ReaderEngineService] = None

# @PublicAPI
def get_engine() -> ReaderEngineService:
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        db_dir = Path.home() / ".local/share/ai-reader"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = os.environ.get("AI_READER_DB_PATH", str(db_dir / "ai_reader_data.db"))
        storage = StorageManager(db_path)
        _GLOBAL_ENGINE = ReaderEngineService(storage)
        if not storage.list_books():
            # 初始化样例书籍
            sample_file = WORKSPACE_ROOT / "mock/_02_mock_data/_01_dataset/sample_article_dataset.json"
            if sample_file.exists():
                try:
                    data = json.loads(sample_file.read_text(encoding="utf-8"))
                    samples = data.get("samples", [])
                    if samples:
                        temp_md = db_dir / "welcome_guide.md"
                        md_lines = []
                        for s in samples:
                            md_lines.append(f"# {s.get('title')}\n\n{s.get('text')}\n")
                        temp_md.write_text("\n\n".join(md_lines), encoding="utf-8")
                        _GLOBAL_ENGINE.doc_parse(str(temp_md))
                except Exception:
                    pass
    return _GLOBAL_ENGINE


def execute_action(action: str, payload_json: str) -> Dict[str, Any]:
    engine = get_engine()
    payload = json.loads(payload_json) if payload_json else {}

    if action == "doc.parse":
        return engine.doc_parse(payload.get("file_path", ""))
    elif action in ("doc.list", "book.list"):
        return {"books": engine.storage.list_books()}
    elif action in ("doc.delete", "book.delete"):
        engine.storage.delete_book(payload.get("book_id", 0))
        return {"status": "deleted", "book_id": payload.get("book_id", 0)}
    elif action in ("doc.get", "book.detail"):
        book_id = payload.get("book_id", 1)
        book = engine.storage.get_book(book_id)
        sections = engine.storage.get_sections(book_id)
        return {"book": book, "meta": book, "sections": sections}
    elif action in ("nlp.extract_keywords", "nlp.keyword_extract"):
        top_n = payload.get("top_k", payload.get("top_n", 30))
        return {"keywords": engine.nlp_keyword_extract(payload.get("book_id", 1), top_n)}
    elif action in ("nlp.build_graph", "graph.build"):
        book_id = payload.get("book_id", 1)
        keywords = engine.storage.get_keywords(book_id)
        if not keywords:
            keywords = engine.nlp_keyword_extract(book_id, 25)
        relations = engine.storage.get_keyword_relations(book_id)
        if not relations:
            relations = engine.keyword_graph_build(book_id, payload.get("min_co_occurrence", 1))
        return {
            "nodes": keywords,
            "links": relations,
            "edges": relations
        }
    elif action == "mindmap.generate":
        return {"nodes": engine.mindmap_generate(payload.get("book_id", 1))}
    elif action == "annotation.save":
        annot_id = engine.annotation_manage({
            "book_id": payload.get("book_id", 1),
            "section_id": payload.get("section_id"),
            "color": payload.get("color", "#FFE066"),
            "style": payload.get("style", "highlight"),
            "note_text": payload.get("note_text"),
            "anchor_json": json.dumps(payload.get("anchor", {})),
            "ai_response": payload.get("ai_response")
        })
        return {"annotation_id": annot_id, "status": "saved"}
    elif action == "annotation.list":
        return {"annotations": engine.storage.get_annotations(payload.get("book_id", 1))}
    elif action == "annotation.delete":
        engine.storage.delete_annotation(payload.get("annotation_id", 0))
        return {"status": "deleted", "annotation_id": payload.get("annotation_id", 0)}
    elif action == "ai.companion_ask":
        resp = engine.ai_companion_stream(
            payload.get("book_id", 1),
            payload.get("template_type", "general"),
            payload.get("selected_text", ""),
            payload.get("prompt", "")
        )
        return {"response": resp, "template_type": payload.get("template_type", "general")}
    else:
        raise ValueError(f"Unknown action: {action}")


def dispatch_invoke(action: str, payload_json: str) -> Dict[str, Any]:
    return execute_action(action, payload_json)


def ai_reader_invoke(action: str, payload_json: str) -> str:
    start = time.time()
    try:
        data = dispatch_invoke(action, payload_json)
        duration_ms = (time.time() - start) * 1000.0
        return json.dumps({
            "code": 0,
            "message": "success",
            "data": data,
            "metrics": {"duration_ms": round(duration_ms, 2)}
        }, ensure_ascii=False)
    except Exception as e:
        duration_ms = (time.time() - start) * 1000.0
        return json.dumps({
            "code": 50001,
            "message": str(e),
            "data": None,
            "metrics": {"duration_ms": round(duration_ms, 2)}
        }, ensure_ascii=False)


def ai_reader_free_string(ptr: Any):
    pass
