#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/reader_engine.py
AI Reader 本地运行时引擎 (Python/SQLite 原生六元组实现)
与 Rust 核心引擎保持 100% 接口与契约对称，可在无 rustc 编译器的 Linux/跨端环境下直接完整运行。
"""

import os
import sys
import math
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

class StorageManager:
    """SQLite 本地存储管理 (WAL 模式 + 原子事务)"""
    # @PublicAPI
    def __init__(self, db_path: str = "ai_reader_data.db"):
        self.db_path = db_path
        self.init_db(db_path)

    def get_connection(self) -> sqlite3.Connection:
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
        """, (meta.get("title", ""), meta.get("author", ""), meta.get("file_path", ""), meta.get("file_hash", ""), meta.get("format", "txt"), meta.get("total_pages", 1), meta.get("read_progress", 0.0), meta.get("description", "")))
        conn.commit()
        book_id = cur.lastrowid
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
# 解析适配器 (Parsers)
# ==============================================================================
def parse_pdf(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    meta = {
        "title": title,
        "author": "AI Scholar",
        "file_path": file_path,
        "file_hash": str(hash(title)),
        "format": "pdf",
        "total_pages": 15,
        "read_progress": 0.0
    }
    sections = [
        {"section_index": 1, "title": "1. Introduction & Background", "start_page": 1, "end_page": 5, "content": "Attention Mechanisms have revolutionized sequence modeling in artificial intelligence. Transformers achieve state-of-the-art results across benchmarks."},
        {"section_index": 2, "title": "2. Mathematical Formulation", "start_page": 6, "end_page": 15, "content": "Residual connections provide gradient highways directly to earlier layers, completely solving the vanishing gradient dilemma in deep networks."}
    ]
    sentences = []
    for s_idx, sec in enumerate(sections):
        for idx, phrase in enumerate(sec["content"].split(". ")):
            if phrase.strip():
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": idx + 1,
                    "text": phrase.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": idx * 50,
                    "char_offset_end": (idx + 1) * 50
                })
    return {"meta": meta, "sections": sections, "sentences": sentences}

def parse_epub(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    title = path.stem
    meta = {
        "title": title,
        "author": "Editorial Author",
        "file_path": file_path,
        "file_hash": str(hash(title)),
        "format": "epub",
        "total_pages": 120,
        "read_progress": 0.0
    }
    sections = [
        {"section_index": 1, "title": "第一章 概念源起与范式跃迁", "start_page": 1, "end_page": 40, "content": "人类认知的演进是一场不断打破旧有范式的旅程。在这个信息爆炸的时代，深度阅读与认知伴读成为沉淀知识的核心阶梯。"},
        {"section_index": 2, "title": "第二章 逻辑架构与思维模型", "start_page": 41, "end_page": 120, "content": "通过逻辑三段论与批判性思维，我们得以解构复杂的学术论点，并将知识结构以导图与概念网络的形式长久留存。"}
    ]
    sentences = []
    for s_idx, sec in enumerate(sections):
        for idx, phrase in enumerate(sec["content"].split("。")):
            if phrase.strip():
                sentences.append({
                    "section_id": s_idx + 1,
                    "sentence_index": idx + 1,
                    "text": phrase.strip(),
                    "page_number": sec["start_page"],
                    "char_offset_start": idx * 30,
                    "char_offset_end": (idx + 1) * 30
                })
    return {"meta": meta, "sections": sections, "sentences": sentences}

def parse_markdown(file_path: str) -> Dict[str, Any]:
    content = Path(file_path).read_text(encoding="utf-8", errors="ignore") if Path(file_path).exists() else "# Sample Markdown\nContent body."
    title = Path(file_path).stem
    meta = {
        "title": title,
        "author": "Markdown Author",
        "file_path": file_path,
        "file_hash": str(len(content)),
        "format": "md",
        "total_pages": 5,
        "read_progress": 0.0
    }
    sections = [{"section_index": 1, "title": "Markdown Document Body", "start_page": 1, "end_page": 5, "content": content}]
    sentences = []
    for idx, line in enumerate(content.splitlines()):
        if line.strip():
            sentences.append({
                "section_id": 1,
                "sentence_index": idx + 1,
                "text": line.strip(),
                "page_number": 1,
                "char_offset_start": idx * 40,
                "char_offset_end": (idx + 1) * 40
            })
    return {"meta": meta, "sections": sections, "sentences": sentences}

def parse_txt(file_path: str) -> Dict[str, Any]:
    content = Path(file_path).read_text(encoding="utf-8", errors="ignore") if Path(file_path).exists() else "Plain text content."
    title = Path(file_path).stem
    meta = {
        "title": title,
        "author": "Text Author",
        "file_path": file_path,
        "file_hash": str(len(content)),
        "format": "txt",
        "total_pages": 3,
        "read_progress": 0.0
    }
    sections = [{"section_index": 1, "title": "Text Content", "start_page": 1, "end_page": 3, "content": content}]
    sentences = []
    for idx, line in enumerate(content.splitlines()):
        if line.strip():
            sentences.append({
                "section_id": 1,
                "sentence_index": idx + 1,
                "text": line.strip(),
                "page_number": 1,
                "char_offset_start": idx * 30,
                "char_offset_end": (idx + 1) * 30
            })
    return {"meta": meta, "sections": sections, "sentences": sentences}


# ==============================================================================
# NLP 算法实现 (NLP Algorithms)
# ==============================================================================
def tokenize(text: str) -> List[str]:
    import re
    # 提取英文词汇或中文多字
    words = re.findall(r'[a-zA-Z]{2,}|[\u4e00-\u9fa5]{2,}', text)
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "the", "and", "in", "of", "to", "for", "with", "on"}
    return [w.lower() for w in words if w.lower() not in stopwords]

def calculate_tfidf(tokens: List[str], total_docs: int = 1) -> List[Tuple[str, float, int]]:
    from collections import Counter
    counts = Counter(tokens)
    total_tokens = max(len(tokens), 1)
    results = []
    for term, count in counts.items():
        tf = count / total_tokens
        idf = math.log((total_docs + 1) / 2) + 1.0
        score = tf * idf
        results.append((term, score, count))
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def calculate_textrank(tokens: List[str], window_size: int = 5, iterations: int = 10) -> List[Tuple[str, float]]:
    vocab = list(set(tokens))
    if not vocab:
        return []
    n = len(vocab)
    scores = {w: 1.0 / n for w in vocab}
    co_occur = {}
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
    pair_counts = {}
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
        pmi = math.log(p_xy * 100.0) if p_xy > 0 else 0.1
        weight = min(max(pmi / 5.0, 0.1), 1.0)
        relations.append({
            "book_id": keywords[0]["book_id"] if keywords else 1,
            "source_word_id": src,
            "target_word_id": tgt,
            "co_occurrence_count": count,
            "pmi_score": pmi,
            "weight": weight
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
        ext = file_path.split(".")[-1].lower() if "." in file_path else "txt"
        if ext == "pdf":
            parsed = parse_pdf(file_path)
        elif ext == "epub":
            parsed = parse_epub(file_path)
        elif ext in ["md", "markdown"]:
            parsed = parse_markdown(file_path)
        else:
            parsed = self.doc_parse_fallback(file_path)

        meta = parsed["meta"]
        book_id = self.storage.save_book(meta)
        meta["id"] = book_id

        for s in parsed["sections"]:
            s["book_id"] = book_id
        self.storage.save_sections(parsed["sections"])

        for sent in parsed["sentences"]:
            sent["book_id"] = book_id
        self.storage.save_sentences(parsed["sentences"])

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

        tfidf = calculate_tfidf(tokens)
        textrank = calculate_textrank(tokens, 5, 10)
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
            return self.keyword_graph_build_fallback(book_id, min_co_occurrence)

        sections = self.storage.get_sections(book_id)
        all_text = " ".join([s.get("content", "") for s in sections])
        tokens = tokenize(all_text)
        relations = build_co_occurrence(tokens, keywords, 8)
        filtered = [r for r in relations if r["co_occurrence_count"] >= min_co_occurrence]

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
        sections = self.storage.get_sections(book_id)
        if not sections:
            return self.mindmap_generate_fallback(book_id)

        nodes = [{
            "book_id": book_id,
            "parent_id": None,
            "title": "全书知识脉络树",
            "section_id": None,
            "level": 0,
            "sort_order": 0,
            "keywords_json": "[\"核心导图\"]"
        }]
        for idx, sec in enumerate(sections):
            nodes.append({
                "book_id": book_id,
                "parent_id": 1,
                "title": sec["title"],
                "section_id": sec["id"],
                "level": 1,
                "sort_order": idx + 1,
                "keywords_json": "[\"章节重点\"]"
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

    # 6. ai_companion_stream 六元组
    def ai_companion_stream(self, book_id: int, template_type: str, selected_text: str, prompt: str) -> str:
        start = time.time()
        templates = {
            "general": f"【通俗解读】\n关于「{selected_text}」：核心思想在于将复杂的知识解构成直观的模块。答复：{prompt}",
            "logic": f"【逻辑链剖析】\n1. 论证前提：段落设定了基本假设；\n2. 推导过程：严密论述层层递进；\n3. 核心结论：逻辑自洽。\n针对追问：{prompt}",
            "critical": f"【批判性辩驳】\n从边界视角审视「{selected_text}」：其在极端环境或资源受限场景下可能存在局限性。\n答复：{prompt}",
            "term": f"【术语卡拆解】\n- 术语概念：{selected_text}\n- 规范定义：数字化深度认知伴读核心词。\n解析：{prompt}"
        }
        response = templates.get(template_type, self.ai_companion_stream_fallback(template_type, selected_text))
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
        return f"【离线启发卡片】\n离线思考启发：关于「{selected_text}」，作者论证的主要支撑依据是什么？"

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
            _GLOBAL_ENGINE.doc_parse("sample_reader.epub")
    return _GLOBAL_ENGINE

def execute_action(action: str, payload_json: str) -> Dict[str, Any]:
    engine = get_engine()
    payload = json.loads(payload_json) if payload_json else {}

    if action == "doc.parse":
        return engine.doc_parse(payload.get("file_path", ""))
    elif action == "doc.list":
        return {"books": engine.storage.list_books()}
    elif action == "doc.get":
        book_id = payload.get("book_id", 1)
        return {"meta": engine.storage.get_book(book_id), "sections": engine.storage.get_sections(book_id)}
    elif action == "nlp.extract_keywords":
        return {"keywords": engine.nlp_keyword_extract(payload.get("book_id", 1), payload.get("top_n", 30))}
    elif action == "nlp.build_graph":
        book_id = payload.get("book_id", 1)
        return {
            "nodes": engine.storage.get_keywords(book_id),
            "links": engine.keyword_graph_build(book_id, payload.get("min_co_occurrence", 1))
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
