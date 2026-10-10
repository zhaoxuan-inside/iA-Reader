-- U1.0.0__init_reader_schema.sql
-- 回滚 V1.0.0 初始化数据库表结构

DROP INDEX IF EXISTS idx_ai_conversation_book;
DROP INDEX IF EXISTS idx_annotation_book;
DROP INDEX IF EXISTS idx_mindmap_book_parent;
DROP INDEX IF EXISTS idx_keyword_rel_book;
DROP INDEX IF EXISTS idx_keyword_book_word;
DROP INDEX IF EXISTS idx_sentence_section_id;
DROP INDEX IF EXISTS idx_book_section_book_id;

DROP TABLE IF EXISTS ai_conversation;
DROP TABLE IF EXISTS annotation;
DROP TABLE IF EXISTS mindmap_node;
DROP TABLE IF EXISTS keyword_relation;
DROP TABLE IF EXISTS keyword_node;
DROP TABLE IF EXISTS sentence_node;
DROP TABLE IF EXISTS book_section;
DROP TABLE IF EXISTS book_meta;
