-- V1.0.0__init_reader_schema.sql
-- AI Reader 核心数据库初始化脚本 (遵循 hs-dev-skill 强制审计字段与规范)

-- 1. 书籍元数据表 (book_meta)
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

-- 2. 章节实体表 (book_section)
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

-- 3. 句子语义节点表 (sentence_node)
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

-- 4. 关键词节点表 (keyword_node)
CREATE TABLE IF NOT EXISTS keyword_node (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    is_del INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    book_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'book', -- 'book' | 'section' | 'sentence'
    tfidf_score REAL NOT NULL DEFAULT 0.0,
    textrank_score REAL NOT NULL DEFAULT 0.0,
    frequency INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
);

-- 5. 关键词关联与共现表 (keyword_relation)
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
    FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE,
    FOREIGN KEY(source_word_id) REFERENCES keyword_node(id) ON DELETE CASCADE,
    FOREIGN KEY(target_word_id) REFERENCES keyword_node(id) ON DELETE CASCADE
);

-- 6. 思维导图节点表 (mindmap_node)
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

-- 7. 文本高亮与边注表 (annotation)
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
    style TEXT NOT NULL DEFAULT 'highlight', -- 'highlight' | 'underline' | 'margin_note'
    note_text TEXT,
    anchor_json TEXT NOT NULL, -- 包含 page, char_offset_start, char_offset_end, rects
    ai_response TEXT,
    FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
);

-- 8. AI 伴读对话记录表 (ai_conversation)
CREATE TABLE IF NOT EXISTS ai_conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    is_del INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    book_id INTEGER NOT NULL,
    section_id INTEGER,
    template_type TEXT NOT NULL DEFAULT 'general', -- 'general' | 'logic' | 'critical' | 'term'
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(book_id) REFERENCES book_meta(id) ON DELETE CASCADE
);

-- 索引构建
CREATE INDEX IF NOT EXISTS idx_book_section_book_id ON book_section(book_id);
CREATE INDEX IF NOT EXISTS idx_sentence_section_id ON sentence_node(section_id);
CREATE INDEX IF NOT EXISTS idx_keyword_book_word ON keyword_node(book_id, word);
CREATE INDEX IF NOT EXISTS idx_keyword_rel_book ON keyword_relation(book_id);
CREATE INDEX IF NOT EXISTS idx_mindmap_book_parent ON mindmap_node(book_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_annotation_book ON annotation(book_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_book ON ai_conversation(book_id);
