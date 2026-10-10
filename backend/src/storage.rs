// backend/src/storage.rs
// SQLite 本地存储实现 (支持 WAL 模式与原子事务)

use std::path::Path;
use std::sync::{Arc, Mutex};
use rusqlite::{params, Connection, Result};
use crate::domain::*;

#[derive(Clone)]
pub struct SqliteStorage {
    conn: Arc<Mutex<Connection>>,
}

impl SqliteStorage {
    pub fn init_db(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch("
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA foreign_keys = ON;
        ")?;
        let storage = Self {
            conn: Arc::new(Mutex::new(conn)),
        };
        storage.apply_migrations()?;
        Ok(storage)
    }

    pub fn apply_migrations(&self) -> Result<()> {
        let conn = self.get_connection();
        let conn_guard = conn.lock().unwrap();
        conn_guard.execute_batch("
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
                FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
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
        ")?;
        Ok(())
    }

    pub fn get_connection(&self) -> Arc<Mutex<Connection>> {
        Arc::clone(&self.conn)
    }

    pub fn save_book(&self, meta: &BookMeta) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO book_meta (title, author, file_path, file_hash, format, total_pages, read_progress, description, is_del, version)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)
             ON CONFLICT(file_path) DO UPDATE SET title=?1, author=?2, updated_at=CURRENT_TIMESTAMP",
            params![meta.title, meta.author, meta.file_path, meta.file_hash, meta.format, meta.total_pages, meta.read_progress, meta.description],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_book(&self, id: i64) -> Result<Option<BookMeta>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, title, author, file_path, file_hash, format, total_pages, read_progress, last_read_at FROM book_meta WHERE id = ?1 AND is_del = 0")?;
        let mut rows = stmt.query(params![id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(BookMeta {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                title: row.get(6)?,
                author: row.get(7)?,
                file_path: row.get(8)?,
                file_hash: row.get(9)?,
                format: row.get(10)?,
                total_pages: row.get(11)?,
                read_progress: row.get(12)?,
                last_read_at: row.get(13)?,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn list_books(&self) -> Result<Vec<BookMeta>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, title, author, file_path, file_hash, format, total_pages, read_progress, last_read_at FROM book_meta WHERE is_del = 0 ORDER BY updated_at DESC")?;
        let rows = stmt.query_map([], |row| {
            Ok(BookMeta {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                title: row.get(6)?,
                author: row.get(7)?,
                file_path: row.get(8)?,
                file_hash: row.get(9)?,
                format: row.get(10)?,
                total_pages: row.get(11)?,
                read_progress: row.get(12)?,
                last_read_at: row.get(13)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn delete_book(&self, id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("UPDATE book_meta SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn save_sections(&self, sections: &[BookSection]) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("INSERT INTO book_section (book_id, section_index, title, parent_id, start_page, end_page, content, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
        for s in sections {
            stmt.execute(params![s.book_id, s.section_index, s.title, s.parent_id, s.start_page, s.end_page, s.content])?;
        }
        Ok(())
    }

    pub fn get_sections(&self, book_id: i64) -> Result<Vec<BookSection>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_index, title, parent_id, start_page, end_page, content FROM book_section WHERE book_id = ?1 AND is_del = 0 ORDER BY section_index ASC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(BookSection {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                section_index: row.get(7)?,
                title: row.get(8)?,
                parent_id: row.get(9)?,
                start_page: row.get(10)?,
                end_page: row.get(11)?,
                content: row.get(12)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_sentences(&self, sentences: &[SentenceNode]) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("INSERT INTO sentence_node (book_id, section_id, sentence_index, text, page_number, char_offset_start, char_offset_end, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
        for s in sentences {
            stmt.execute(params![s.book_id, s.section_id, s.sentence_index, s.text, s.page_number, s.char_offset_start, s.char_offset_end])?;
        }
        Ok(())
    }

    pub fn get_sentences(&self, section_id: i64) -> Result<Vec<SentenceNode>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, sentence_index, text, page_number, char_offset_start, char_offset_end FROM sentence_node WHERE section_id = ?1 AND is_del = 0 ORDER BY sentence_index ASC")?;
        let rows = stmt.query_map(params![section_id], |row| {
            Ok(SentenceNode {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                section_id: row.get(7)?,
                sentence_index: row.get(8)?,
                text: row.get(9)?,
                page_number: row.get(10)?,
                char_offset_start: row.get(11)?,
                char_offset_end: row.get(12)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_keywords(&self, keywords: &[KeywordNode]) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("INSERT INTO keyword_node (book_id, word, level, tfidf_score, textrank_score, frequency, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, 1)")?;
        for k in keywords {
            stmt.execute(params![k.book_id, k.word, k.level, k.tfidf_score, k.textrank_score, k.frequency])?;
        }
        Ok(())
    }

    pub fn get_keywords(&self, book_id: i64) -> Result<Vec<KeywordNode>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, word, level, tfidf_score, textrank_score, frequency FROM keyword_node WHERE book_id = ?1 AND is_del = 0 ORDER BY textrank_score DESC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(KeywordNode {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                word: row.get(7)?,
                level: row.get(8)?,
                tfidf_score: row.get(9)?,
                textrank_score: row.get(10)?,
                frequency: row.get(11)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_keyword_relations(&self, relations: &[KeywordRelation]) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("INSERT INTO keyword_relation (book_id, source_word_id, target_word_id, co_occurrence_count, pmi_score, weight, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, 1)")?;
        for r in relations {
            stmt.execute(params![r.book_id, r.source_word_id, r.target_word_id, r.co_occurrence_count, r.pmi_score, r.weight])?;
        }
        Ok(())
    }

    pub fn get_keyword_relations(&self, book_id: i64) -> Result<Vec<KeywordRelation>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, source_word_id, target_word_id, co_occurrence_count, pmi_score, weight FROM keyword_relation WHERE book_id = ?1 AND is_del = 0 ORDER BY weight DESC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(KeywordRelation {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                source_word_id: row.get(7)?,
                target_word_id: row.get(8)?,
                co_occurrence_count: row.get(9)?,
                pmi_score: row.get(10)?,
                weight: row.get(11)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_mindmap_nodes(&self, nodes: &[MindmapNode]) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("INSERT INTO mindmap_node (book_id, parent_id, title, section_id, level, sort_order, keywords_json, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
        for n in nodes {
            stmt.execute(params![n.book_id, n.parent_id, n.title, n.section_id, n.level, n.sort_order, n.keywords_json])?;
        }
        Ok(())
    }

    pub fn get_mindmap_nodes(&self, book_id: i64) -> Result<Vec<MindmapNode>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, parent_id, title, section_id, level, sort_order, keywords_json FROM mindmap_node WHERE book_id = ?1 AND is_del = 0 ORDER BY level ASC, sort_order ASC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(MindmapNode {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                parent_id: row.get(7)?,
                title: row.get(8)?,
                section_id: row.get(9)?,
                level: row.get(10)?,
                sort_order: row.get(11)?,
                keywords_json: row.get(12)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_annotation(&self, a: &Annotation) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO annotation (book_id, section_id, color, style, note_text, anchor_json, ai_response, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)",
            params![a.book_id, a.section_id, a.color, a.style, a.note_text, a.anchor_json, a.ai_response],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_annotations(&self, book_id: i64) -> Result<Vec<Annotation>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, color, style, note_text, anchor_json, ai_response FROM annotation WHERE book_id = ?1 AND is_del = 0 ORDER BY id ASC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(Annotation {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                section_id: row.get(7)?,
                color: row.get(8)?,
                style: row.get(9)?,
                note_text: row.get(10)?,
                anchor_json: row.get(11)?,
                ai_response: row.get(12)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn delete_annotation(&self, id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("UPDATE annotation SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn save_ai_conversation(&self, conv: &AiConversation) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO ai_conversation (book_id, section_id, template_type, prompt, response, latency_ms, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, 1)",
            params![conv.book_id, conv.section_id, conv.template_type, conv.prompt, conv.response, conv.latency_ms],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_ai_conversations(&self, book_id: i64) -> Result<Vec<AiConversation>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, template_type, prompt, response, latency_ms FROM ai_conversation WHERE book_id = ?1 AND is_del = 0 ORDER BY id ASC")?;
        let rows = stmt.query_map(params![book_id], |row| {
            Ok(AiConversation {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                section_id: row.get(7)?,
                template_type: row.get(8)?,
                prompt: row.get(9)?,
                response: row.get(10)?,
                latency_ms: row.get(11)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }
}
