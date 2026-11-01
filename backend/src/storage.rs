// backend/src/storage.rs
// SQLite 本地存储实现（WAL + 事务 + user_version 版本化迁移）
//
// 数据完整性契约：
// - 多行写入（章节/段落/句子/关键词/导图/设置/整书落库）一律在单事务内完成，
//   中途失败整体回滚——此前逐条 autocommit，半成品数据会静默留存；
// - schema 通过 PRAGMA user_version 版本化迁移，改表有路径、老库可升级。

use std::sync::{Arc, Mutex};
use std::collections::HashMap;
use rusqlite::{params, Connection, OptionalExtension, Result};
use crate::domain::*;

/// 当前 schema 版本（PRAGMA user_version）
const SCHEMA_VERSION: i32 = 2;

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

    /// v1 基线 schema（不含 v2 增量列；新列由迁移补齐，新老库走同一条路径）
    const V1_SCHEMA: &'static str = "
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

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            is_del INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            value TEXT NOT NULL
        );
    ";

    /// v2 增量：段落节点表 + 幂等归档唯一索引 + 高频查询索引
    const V2_SCHEMA: &'static str = "
        CREATE TABLE IF NOT EXISTS paragraph_node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            is_del INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            book_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            paragraph_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            page_number INTEGER NOT NULL DEFAULT 1,
            char_offset_start INTEGER NOT NULL DEFAULT 0,
            char_offset_end INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_paragraph_section
            ON paragraph_node(section_id, paragraph_index);
        CREATE INDEX IF NOT EXISTS idx_sentence_section
            ON sentence_node(section_id, sentence_index);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_annotation_idem
            ON annotation(book_id, idem_key)
            WHERE idem_key IS NOT NULL AND is_del = 0;
    ";

    pub fn apply_migrations(&self) -> Result<()> {
        let conn = self.get_connection();
        let mut guard = conn.lock().unwrap();
        let version: i32 = guard.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version >= SCHEMA_VERSION {
            return Ok(());
        }
        if version < 1 {
            guard.execute_batch(Self::V1_SCHEMA)?;
        }
        // v2 增量列：column_exists 守护，老库补列、新库幂等跳过
        Self::add_column_if_missing(&mut guard, "book_meta", "read_section_id", "INTEGER")?;
        Self::add_column_if_missing(&mut guard, "book_meta", "read_paragraph_index", "INTEGER NOT NULL DEFAULT 0")?;
        Self::add_column_if_missing(&mut guard, "book_meta", "read_char_offset", "INTEGER NOT NULL DEFAULT 0")?;
        Self::add_column_if_missing(&mut guard, "book_section", "level", "INTEGER NOT NULL DEFAULT 1")?;
        Self::add_column_if_missing(&mut guard, "annotation", "origin", "TEXT NOT NULL DEFAULT 'manual'")?;
        Self::add_column_if_missing(&mut guard, "annotation", "idem_key", "TEXT")?;
        Self::add_column_if_missing(&mut guard, "ai_conversation", "thread_id", "TEXT")?;
        guard.execute_batch(Self::V2_SCHEMA)?;
        guard.pragma_update(None, "user_version", SCHEMA_VERSION)?;
        Ok(())
    }

    fn add_column_if_missing(conn: &mut Connection, table: &str, column: &str, ddl: &str) -> Result<()> {
        if Self::column_exists(conn, table, column)? {
            return Ok(());
        }
        conn.execute_batch(&format!("ALTER TABLE {} ADD COLUMN {} {};", table, column, ddl))
    }

    fn column_exists(conn: &Connection, table: &str, column: &str) -> Result<bool> {
        let mut stmt = conn.prepare(&format!("PRAGMA table_info({})", table))?;
        let mut rows = stmt.query([])?;
        while let Some(row) = rows.next()? {
            let name: String = row.get(1)?;
            if name == column {
                return Ok(true);
            }
        }
        Ok(false)
    }

    pub fn get_connection(&self) -> Arc<Mutex<Connection>> {
        Arc::clone(&self.conn)
    }

    pub fn save_book(&self, meta: &BookMeta) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        // RETURNING id：upsert 走 UPDATE 臂时不推进 last_insert_rowid()，
        // 陈旧 id 会让派生数据挂到不存在的 book 上（FOREIGN KEY 失败或脏写）
        let id: i64 = conn.query_row(
            "INSERT INTO book_meta (title, author, file_path, file_hash, format, total_pages, read_progress, description, is_del, version)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)
             ON CONFLICT(file_path) DO UPDATE SET title=?1, author=?2, updated_at=CURRENT_TIMESTAMP
             RETURNING id",
            params![meta.title, meta.author, meta.file_path, meta.file_hash, meta.format, meta.total_pages, meta.read_progress, meta.description],
            |row| row.get(0),
        )?;
        Ok(id)
    }

    pub fn find_book_id_by_hash(&self, file_hash: &str) -> Result<Option<i64>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id FROM book_meta WHERE file_hash = ?1 AND is_del = 0 LIMIT 1",
        )?;
        let mut rows = stmt.query(params![file_hash])?;
        if let Some(row) = rows.next()? {
            Ok(Some(row.get(0)?))
        } else {
            Ok(None)
        }
    }

    /// 整书原子落库（FEAT-001 REQ-007）：book upsert + 派生数据重建（章节/段落/句子）
    /// 在同一事务内完成，任何一步失败整体回滚，不再留下半成品。
    /// sections[].id 尚未分配，paragraphs/sentences 的 section_id 为 1-based 章节序号占位，
    /// 事务内回填真实章节 id。
    pub fn save_parsed_book(
        &self,
        meta: &BookMeta,
        sections: &[BookSection],
        paragraphs: &[ParagraphNode],
        sentences: &[SentenceNode],
    ) -> Result<i64> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        let book_id: i64 = tx.query_row(
            "INSERT INTO book_meta (title, author, file_path, file_hash, format, total_pages, read_progress, description, is_del, version)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)
             ON CONFLICT(file_path) DO UPDATE SET title=?1, author=?2, updated_at=CURRENT_TIMESTAMP
             RETURNING id",
            params![meta.title, meta.author, meta.file_path, meta.file_hash, meta.format, meta.total_pages, meta.read_progress, meta.description],
            |row| row.get(0),
        )?;

        // 同路径换内容再导（upsert 命中已有行）：派生数据整体重建；
        // 批注与伴读会话按 book_id 保留
        for table in [
            "book_section",
            "paragraph_node",
            "sentence_node",
            "keyword_node",
            "keyword_relation",
            "mindmap_node",
        ] {
            tx.execute(&format!("DELETE FROM {} WHERE book_id = ?1", table), params![book_id])?;
        }

        let mut section_ids: Vec<i64> = Vec::with_capacity(sections.len());
        {
            let mut stmt = tx.prepare("INSERT INTO book_section (book_id, section_index, title, level, parent_id, start_page, end_page, content, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)")?;
            for s in sections {
                stmt.execute(params![book_id, s.section_index, s.title, s.level, s.parent_id, s.start_page, s.end_page, s.content])?;
                section_ids.push(tx.last_insert_rowid());
            }
        }
        {
            let mut stmt = tx.prepare("INSERT INTO paragraph_node (book_id, section_id, paragraph_index, text, page_number, char_offset_start, char_offset_end, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
            for p in paragraphs {
                let sid = section_id_for(&section_ids, p.section_id)?;
                stmt.execute(params![book_id, sid, p.paragraph_index, p.text, p.page_number, p.char_offset_start, p.char_offset_end])?;
            }
        }
        {
            let mut stmt = tx.prepare("INSERT INTO sentence_node (book_id, section_id, sentence_index, text, page_number, char_offset_start, char_offset_end, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
            for s in sentences {
                let sid = section_id_for(&section_ids, s.section_id)?;
                stmt.execute(params![book_id, sid, s.sentence_index, s.text, s.page_number, s.char_offset_start, s.char_offset_end])?;
            }
        }
        tx.commit()?;
        Ok(book_id)
    }

    /// 重建派生数据前清空旧章节/段落/句子/关键词/关系/导图；批注与伴读会话按 book_id 保留
    pub fn delete_book_derived_data(&self, book_id: i64) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        for table in ["book_section", "paragraph_node", "sentence_node", "keyword_node", "keyword_relation", "mindmap_node"] {
            tx.execute(&format!("DELETE FROM {} WHERE book_id = ?1", table), params![book_id])?;
        }
        tx.commit()
    }

    pub fn get_book(&self, id: i64) -> Result<Option<BookMeta>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, title, author, file_path, file_hash, format, total_pages, read_progress, last_read_at, read_section_id, read_paragraph_index, read_char_offset FROM book_meta WHERE id = ?1 AND is_del = 0")?;
        let mut rows = stmt.query(params![id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(Self::book_meta_from_row(row)?))
        } else {
            Ok(None)
        }
    }

    pub fn list_books(&self) -> Result<Vec<BookMeta>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, title, author, file_path, file_hash, format, total_pages, read_progress, last_read_at, read_section_id, read_paragraph_index, read_char_offset FROM book_meta WHERE is_del = 0 ORDER BY COALESCE(last_read_at, updated_at) DESC")?;
        let rows = stmt.query_map([], Self::book_meta_from_row)?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    fn book_meta_from_row(row: &rusqlite::Row<'_>) -> Result<BookMeta> {
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
            read_section_id: row.get(14)?,
            read_paragraph_index: row.get(15)?,
            read_char_offset: row.get(16)?,
        })
    }

    /// 续读进度落库（FEAT-002 REQ-005）：锚点 + 进度比 + last_read_at 一次写入
    pub fn save_read_progress(
        &self,
        book_id: i64,
        section_id: Option<i64>,
        paragraph_index: i32,
        char_offset: i32,
        progress: f64,
    ) -> Result<bool> {
        let conn = self.conn.lock().unwrap();
        let changed = conn.execute(
            "UPDATE book_meta SET read_section_id = ?2, read_paragraph_index = ?3, read_char_offset = ?4, \
             read_progress = ?5, last_read_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP \
             WHERE id = ?1 AND is_del = 0",
            params![book_id, section_id, paragraph_index, char_offset, progress.clamp(0.0, 1.0)],
        )?;
        Ok(changed > 0)
    }

    /// 打开书籍即视为阅读行为：刷新 last_read_at（书库按最近阅读排序的依据）
    pub fn touch_last_read(&self, book_id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE book_meta SET last_read_at = CURRENT_TIMESTAMP WHERE id = ?1 AND is_del = 0",
            params![book_id],
        )?;
        Ok(())
    }

    pub fn delete_book(&self, id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("UPDATE book_meta SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?1", params![id])?;
        Ok(())
    }

    /// 删除书籍（FEAT-001 书库管理）：先物理清理批注/伴读会话/派生数据，再软删主记录。
    /// 软删保留 book_meta 行以维持审计轨迹；派生行无独立消费价值，直接清除。
    pub fn delete_book_full(&self, id: i64) -> Result<bool> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        let exists: bool = tx
            .query_row(
                "SELECT COUNT(*) FROM book_meta WHERE id = ?1 AND is_del = 0",
                params![id],
                |row| row.get::<_, i64>(0),
            )
            .map(|n| n > 0)?;
        if !exists {
            return Ok(false);
        }
        for table in [
            "annotation",
            "ai_conversation",
            "book_section",
            "paragraph_node",
            "sentence_node",
            "keyword_node",
            "keyword_relation",
            "mindmap_node",
        ] {
            tx.execute(&format!("DELETE FROM {} WHERE book_id = ?1", table), params![id])?;
        }
        tx.execute(
            "UPDATE book_meta SET is_del = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?1",
            params![id],
        )?;
        tx.commit()?;
        Ok(true)
    }

    /// 应用配置读取（app_settings 键值表）：keys 为空返回全部
    pub fn get_app_settings(&self, keys: &[String]) -> Result<HashMap<String, String>> {
        let conn = self.conn.lock().unwrap();
        let mut out = HashMap::new();
        if keys.is_empty() {
            let mut stmt = conn
                .prepare("SELECT key, value FROM app_settings WHERE is_del = 0")?;
            let rows = stmt.query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)))?;
            for r in rows {
                let (k, v) = r?;
                out.insert(k, v);
            }
        } else {
            let mut stmt = conn
                .prepare("SELECT key, value FROM app_settings WHERE is_del = 0 AND key = ?1")?;
            for key in keys {
                if let Ok(v) = stmt.query_row(params![key], |row| row.get::<_, String>(1)) {
                    out.insert(key.clone(), v);
                }
            }
        }
        Ok(out)
    }

    /// 应用配置保存：逐键 upsert（部分更新语义），单事务保证批量一致
    pub fn save_app_settings(&self, settings: &HashMap<String, String>) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        for (k, v) in settings {
            tx.execute(
                "INSERT INTO app_settings (key, value, is_del, version) VALUES (?1, ?2, 0, 1)
                 ON CONFLICT(key) DO UPDATE SET value = ?2, updated_at = CURRENT_TIMESTAMP",
                params![k, v],
            )?;
        }
        tx.commit()
    }

    /// 返回按入参顺序落库后的真实章节 id（paragraph/sentence 外键需要）
    pub fn save_sections(&self, sections: &[BookSection]) -> Result<Vec<i64>> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        let mut ids = Vec::with_capacity(sections.len());
        {
            let mut stmt = tx.prepare("INSERT INTO book_section (book_id, section_index, title, level, parent_id, start_page, end_page, content, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)")?;
            for s in sections {
                stmt.execute(params![s.book_id, s.section_index, s.title, s.level, s.parent_id, s.start_page, s.end_page, s.content])?;
                ids.push(tx.last_insert_rowid());
            }
        }
        tx.commit()?;
        Ok(ids)
    }

    pub fn count_sections(&self, book_id: i64) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.query_row(
            "SELECT COUNT(*) FROM book_section WHERE book_id = ?1 AND is_del = 0",
            params![book_id],
            |row| row.get(0),
        )
    }

    pub fn get_sections(&self, book_id: i64) -> Result<Vec<BookSection>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_index, title, level, parent_id, start_page, end_page, content FROM book_section WHERE book_id = ?1 AND is_del = 0 ORDER BY section_index ASC")?;
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
                level: row.get(9)?,
                parent_id: row.get(10)?,
                start_page: row.get(11)?,
                end_page: row.get(12)?,
                content: row.get(13)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    pub fn save_paragraphs(&self, paragraphs: &[ParagraphNode]) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        {
            let mut stmt = tx.prepare("INSERT INTO paragraph_node (book_id, section_id, paragraph_index, text, page_number, char_offset_start, char_offset_end, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
            for p in paragraphs {
                stmt.execute(params![p.book_id, p.section_id, p.paragraph_index, p.text, p.page_number, p.char_offset_start, p.char_offset_end])?;
            }
        }
        tx.commit()
    }

    pub fn get_paragraphs(&self, section_id: i64) -> Result<Vec<ParagraphNode>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, paragraph_index, text, page_number, char_offset_start, char_offset_end FROM paragraph_node WHERE section_id = ?1 AND is_del = 0 ORDER BY paragraph_index ASC")?;
        let rows = stmt.query_map(params![section_id], |row| {
            Ok(ParagraphNode {
                id: row.get(0)?,
                created_at: row.get(1)?,
                updated_at: row.get(2)?,
                description: row.get(3)?,
                is_del: row.get(4)?,
                version: row.get(5)?,
                book_id: row.get(6)?,
                section_id: row.get(7)?,
                paragraph_index: row.get(8)?,
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

    pub fn save_sentences(&self, sentences: &[SentenceNode]) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        {
            let mut stmt = tx.prepare("INSERT INTO sentence_node (book_id, section_id, sentence_index, text, page_number, char_offset_start, char_offset_end, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
            for s in sentences {
                stmt.execute(params![s.book_id, s.section_id, s.sentence_index, s.text, s.page_number, s.char_offset_start, s.char_offset_end])?;
            }
        }
        tx.commit()
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

    /// 覆盖式保存：同一 book 重复抽取时先清旧关键词，防止每次调用累积；单事务原子
    pub fn save_keywords(&self, keywords: &[KeywordNode]) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        if let Some(first) = keywords.first() {
            tx.execute("DELETE FROM keyword_node WHERE book_id = ?1", params![first.book_id])?;
        }
        {
            let mut stmt = tx.prepare("INSERT INTO keyword_node (book_id, word, level, tfidf_score, textrank_score, frequency, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, 1)")?;
            for k in keywords {
                stmt.execute(params![k.book_id, k.word, k.level, k.tfidf_score, k.textrank_score, k.frequency])?;
            }
        }
        tx.commit()
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

    /// 覆盖式保存：同一 book 重复构图时先清旧关系边，防止每次调用累积；单事务原子
    pub fn save_keyword_relations(&self, relations: &[KeywordRelation]) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        if let Some(first) = relations.first() {
            tx.execute("DELETE FROM keyword_relation WHERE book_id = ?1", params![first.book_id])?;
        }
        {
            let mut stmt = tx.prepare("INSERT INTO keyword_relation (book_id, source_word_id, target_word_id, co_occurrence_count, pmi_score, weight, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, 1)")?;
            for r in relations {
                stmt.execute(params![r.book_id, r.source_word_id, r.target_word_id, r.co_occurrence_count, r.pmi_score, r.weight])?;
            }
        }
        tx.commit()
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

    /// 导图树覆盖式保存：nodes 按 parent-before-child 拓扑序给出，parent_id 为临时 id，
    /// 落库时换算为真实自增 id——AUTOINCREMENT 全局递增，此前直用临时 id 会让
    /// 非首本书的导图父子关系整体错位（前端孤儿节点兜底掩盖了该 bug）。
    pub fn save_mindmap_nodes(&self, nodes: &[MindmapNode]) -> Result<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        if let Some(first) = nodes.first() {
            tx.execute("DELETE FROM mindmap_node WHERE book_id = ?1", params![first.book_id])?;
        }
        let mut id_map: HashMap<i64, i64> = HashMap::new();
        {
            let mut stmt = tx.prepare("INSERT INTO mindmap_node (book_id, parent_id, title, section_id, level, sort_order, keywords_json, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 0, 1)")?;
            for n in nodes {
                let real_parent: Option<i64> = n.parent_id.and_then(|p| id_map.get(&p).copied());
                stmt.execute(params![n.book_id, real_parent, n.title, n.section_id, n.level, n.sort_order, n.keywords_json])?;
                id_map.insert(n.id, tx.last_insert_rowid());
            }
        }
        tx.commit()
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

    /// 标注落库（FEAT-007 REQ-3/5）：idem_key 命中既有行时直接返回该 id（幂等归档）；
    /// 唯一索引兜底并发下的重复插入。
    pub fn save_annotation(&self, a: &Annotation) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        if let Some(key) = a.idem_key.as_deref().filter(|k| !k.trim().is_empty()) {
            let existing: Option<i64> = conn
                .query_row(
                    "SELECT id FROM annotation WHERE book_id = ?1 AND idem_key = ?2 AND is_del = 0",
                    params![a.book_id, key],
                    |row| row.get(0),
                )
                .optional()?;
            if let Some(id) = existing {
                return Ok(id);
            }
        }
        conn.execute(
            "INSERT INTO annotation (book_id, section_id, color, style, note_text, anchor_json, ai_response, origin, idem_key, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 0, 1)",
            params![a.book_id, a.section_id, a.color, a.style, a.note_text, a.anchor_json, a.ai_response, a.origin, a.idem_key],
        )?;
        Ok(conn.last_insert_rowid())
    }

    /// 幂等归档查询：idem_key 是否已存在（未删除行）
    pub fn find_annotation_id_by_idem(&self, book_id: i64, idem_key: &str) -> Result<Option<i64>> {
        let conn = self.conn.lock().unwrap();
        conn.query_row(
            "SELECT id FROM annotation WHERE book_id = ?1 AND idem_key = ?2 AND is_del = 0",
            params![book_id, idem_key],
            |row| row.get(0),
        )
        .optional()
    }

    pub fn get_annotations(&self, book_id: i64) -> Result<Vec<Annotation>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, color, style, note_text, anchor_json, ai_response, origin, idem_key FROM annotation WHERE book_id = ?1 AND is_del = 0 ORDER BY id ASC")?;
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
                origin: row.get(13)?,
                idem_key: row.get(14)?,
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

    /// 部分更新标注（task_16 D1）：仅覆盖提供的字段，version 自增；软删行不可更新
    pub fn update_annotation(
        &self,
        annotation_id: i64,
        note_text: Option<&str>,
        color: Option<&str>,
        style: Option<&str>,
    ) -> Result<bool> {
        let conn = self.conn.lock().unwrap();
        let changed = conn.execute(
            "UPDATE annotation SET \
             note_text = COALESCE(?2, note_text), \
             color = COALESCE(?3, color), \
             style = COALESCE(?4, style), \
             updated_at = CURRENT_TIMESTAMP, \
             version = version + 1 \
             WHERE id = ?1 AND is_del = 0",
            params![annotation_id, note_text, color, style],
        )?;
        Ok(changed > 0)
    }

    pub fn save_ai_conversation(&self, conv: &AiConversation) -> Result<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO ai_conversation (book_id, section_id, description, template_type, prompt, response, latency_ms, thread_id, is_del, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, 1)",
            params![conv.book_id, conv.section_id, conv.description, conv.template_type, conv.prompt, conv.response, conv.latency_ms, conv.thread_id],
        )?;
        Ok(conn.last_insert_rowid())
    }

    pub fn get_ai_conversations(&self, book_id: i64) -> Result<Vec<AiConversation>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, created_at, updated_at, description, is_del, version, book_id, section_id, template_type, prompt, response, latency_ms, thread_id FROM ai_conversation WHERE book_id = ?1 AND is_del = 0 ORDER BY id ASC")?;
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
                thread_id: row.get(12)?,
            })
        })?;
        let mut res = Vec::new();
        for r in rows {
            res.push(r?);
        }
        Ok(res)
    }

    /// 多轮追问上下文还原（FEAT-005 REQ-003）：按线程 id 取既有轮次（prompt → response），
    /// 依 id 升序拼入 LLM 消息历史。
    pub fn get_thread_history(&self, thread_id: &str, limit: usize) -> Result<Vec<(String, String)>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT prompt, response FROM ai_conversation \
             WHERE thread_id = ?1 AND is_del = 0 ORDER BY id DESC LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![thread_id, limit as i64], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })?;
        let mut out: Vec<(String, String)> = Vec::new();
        for r in rows {
            out.push(r?);
        }
        out.reverse();
        Ok(out)
    }
}

/// 1-based 章节序号占位 → 真实章节 id（save_parsed_book 事务内回填用）
fn section_id_for(section_ids: &[i64], pos: i64) -> Result<i64> {
    let idx = pos - 1;
    if idx < 0 || idx as usize >= section_ids.len() {
        return Err(rusqlite::Error::InvalidParameterName(format!(
            "section position {} out of range (len={})",
            pos,
            section_ids.len()
        )));
    }
    Ok(section_ids[idx as usize])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_db(tag: &str) -> String {
        let path = std::env::temp_dir().join(format!(
            "ai_reader_storage_test_{}_{}.db",
            tag,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        path.to_string_lossy().to_string()
    }

    fn meta(file_path: &str, file_hash: &str) -> BookMeta {
        BookMeta {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            title: "测试书".to_string(),
            author: None,
            file_path: file_path.to_string(),
            file_hash: file_hash.to_string(),
            format: "md".to_string(),
            total_pages: 1,
            read_progress: 0.0,
            last_read_at: None,
            read_section_id: None,
            read_paragraph_index: 0,
            read_char_offset: 0,
        }
    }

    fn section(book_id: i64, index: i32, title: &str, level: i32, parent: Option<i64>) -> BookSection {
        BookSection {
            id: 0,
            created_at: String::new(),
            updated_at: String::new(),
            description: None,
            is_del: 0,
            version: 1,
            book_id,
            section_index: index,
            title: title.to_string(),
            level,
            parent_id: parent,
            start_page: 1,
            end_page: 1,
            content: Some("正文".to_string()),
        }
    }

    #[test]
    fn save_parsed_book_is_atomic_with_real_section_ids() {
        let storage = SqliteStorage::init_db(&temp_db("atomic")).unwrap();
        let sections = vec![section(0, 1, "甲", 1, None), section(0, 2, "乙", 1, None)];
        let paragraphs = vec![
            ParagraphNode { id: 0, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1, book_id: 0, section_id: 1, paragraph_index: 1, text: "甲段".into(), page_number: 1, char_offset_start: 0, char_offset_end: 2 },
            ParagraphNode { id: 0, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1, book_id: 0, section_id: 2, paragraph_index: 1, text: "乙段".into(), page_number: 1, char_offset_start: 3, char_offset_end: 5 },
        ];
        let book_id = storage
            .save_parsed_book(&meta("/tmp/a.md", "hash_a"), &sections, &paragraphs, &[])
            .unwrap();
        let got = storage.get_paragraphs(storage.get_sections(book_id).unwrap()[0].id).unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].text, "甲段");
        // 二次导入（同路径换内容）重建派生数据，不产生残留
        let book_id2 = storage
            .save_parsed_book(&meta("/tmp/a.md", "hash_a2"), &sections, &paragraphs, &[])
            .unwrap();
        assert_eq!(book_id, book_id2, "同路径 upsert 应回到同一本书");
        let all_sections = storage.get_sections(book_id2).unwrap();
        assert_eq!(all_sections.len(), 2, "重建后不得残留旧章节");
        assert_eq!(all_sections[0].level, 1, "level 列应随插入落库");
    }

    #[test]
    fn save_parsed_book_rolls_back_on_bad_section_reference() {
        let storage = SqliteStorage::init_db(&temp_db("rollback")).unwrap();
        let sections = vec![section(0, 1, "甲", 1, None)];
        // paragraph 引用不存在的章节序号 99 → 事务失败，且 book_meta 不得残留
        let bad_paragraph = ParagraphNode { id: 0, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1, book_id: 0, section_id: 99, paragraph_index: 1, text: "孤儿段".into(), page_number: 1, char_offset_start: 0, char_offset_end: 3 };
        assert!(storage
            .save_parsed_book(&meta("/tmp/bad.md", "hash_bad"), &sections, &[bad_paragraph], &[])
            .is_err());
        assert!(storage.list_books().unwrap().is_empty(), "事务回滚后 book_meta 不应残留");
    }

    #[test]
    fn mindmap_parent_ids_map_to_real_rows() {
        let storage = SqliteStorage::init_db(&temp_db("mindmap")).unwrap();
        let book_id = storage.save_book(&meta("/tmp/mm.md", "hash_mm")).unwrap();
        // 先插一本书让 AUTOINCREMENT 前进，再验证第二本书的 parent 映射
        let nodes = vec![
            MindmapNode { id: 1, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1, book_id, parent_id: None, title: "根".into(), section_id: None, level: 0, sort_order: 0, keywords_json: None },
            MindmapNode { id: 2, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1, book_id, parent_id: Some(1), title: "子".into(), section_id: None, level: 1, sort_order: 1, keywords_json: None },
        ];
        storage.save_mindmap_nodes(&nodes).unwrap();
        storage.save_mindmap_nodes(&nodes).unwrap(); // 重复保存（覆盖式）
        let got = storage.get_mindmap_nodes(book_id).unwrap();
        assert_eq!(got.len(), 2);
        let root = got.iter().find(|n| n.level == 0).unwrap();
        let child = got.iter().find(|n| n.level == 1).unwrap();
        assert_eq!(child.parent_id, Some(root.id), "parent_id 必须映射到真实行 id，而非临时 id");
    }

    #[test]
    fn annotation_idem_key_returns_existing_row() {
        let storage = SqliteStorage::init_db(&temp_db("idem")).unwrap();
        let book_id = storage.save_book(&meta("/tmp/an.md", "hash_an")).unwrap();
        let mut a = Annotation {
            id: 0, created_at: String::new(), updated_at: String::new(), description: None, is_del: 0, version: 1,
            book_id, section_id: None, color: "#FFE066".into(), style: "margin_note".into(),
            note_text: Some("AI 边注".into()), anchor_json: "{}".into(), ai_response: Some("回复".into()),
            origin: "companion".into(), idem_key: Some("idem-1".into()),
        };
        let id1 = storage.save_annotation(&a).unwrap();
        a.note_text = Some("重复提交".into());
        let id2 = storage.save_annotation(&a).unwrap();
        assert_eq!(id1, id2, "同 idem_key 重复归档应返回既有行");
        let list = storage.get_annotations(book_id).unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].origin, "companion");
        assert_eq!(list[0].note_text.as_deref(), Some("AI 边注"), "幂等命中不得覆盖原行");
        // 不同 key 正常新插入
        a.idem_key = Some("idem-2".into());
        let id3 = storage.save_annotation(&a).unwrap();
        assert_ne!(id1, id3);
    }

    #[test]
    fn read_progress_roundtrip_and_touch() {
        let storage = SqliteStorage::init_db(&temp_db("progress")).unwrap();
        let book_id = storage.save_book(&meta("/tmp/pg.md", "hash_pg")).unwrap();
        assert!(storage.save_read_progress(book_id, Some(7), 3, 42, 0.65).unwrap());
        let got = storage.get_book(book_id).unwrap().unwrap();
        assert_eq!(got.read_section_id, Some(7));
        assert_eq!(got.read_paragraph_index, 3);
        assert_eq!(got.read_char_offset, 42);
        assert!((got.read_progress - 0.65).abs() < 1e-9);
        assert!(got.last_read_at.is_some(), "进度落库应同时刷新 last_read_at");
    }

    #[test]
    fn migration_v1_legacy_db_upgrades_to_v2() {
        // 模拟 v1 老库：建 V1_SCHEMA 后把 user_version 置 1，再 init 走迁移补列
        let db = temp_db("legacy");
        {
            let conn = Connection::open(&db).unwrap();
            conn.execute_batch(SqliteStorage::V1_SCHEMA).unwrap();
            conn.execute_batch("INSERT INTO book_meta (title, file_path, file_hash, format) VALUES ('旧书', '/tmp/old.md', 'h', 'md')").unwrap();
            conn.pragma_update(None, "user_version", 1).unwrap();
        }
        let storage = SqliteStorage::init_db(&db).unwrap();
        let book = storage.list_books().unwrap().pop().unwrap();
        assert!(book.read_section_id.is_none(), "v1 数据读回时新列应取默认 NULL");
        let sections = vec![section(book.id, 1, "升级节", 2, None)];
        storage.save_sections(&sections).unwrap();
        assert_eq!(storage.get_sections(book.id).unwrap()[0].level, 2, "迁移后 level 列可用");
    }
}
