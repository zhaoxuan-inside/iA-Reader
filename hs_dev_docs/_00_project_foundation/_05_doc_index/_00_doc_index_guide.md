# 文档倒排索引数据库与查询说明 (Doc Index Database)

本目录存放基于 SQLite (FTS5 + LIKE) 构建的高速文档索引缓存：
- **索引数据库**：`doc_index.sqlite`
- **全局文档阅读与导航说明**：请查阅根目录 [hs_dev_docs/_00_docs_compass.md](../../_00_docs_compass.md)
- **常用查询命令**：
  - `python scripts/doc_index_db.py --root . search --q "<关键词>"`
  - `python scripts/doc_index_db.py --root . feature-search --q "<特性名>"`
  - `python scripts/doc_index_db.py --root . method-search --q "<业务意图>"`
  - `python scripts/doc_index_db.py --root . symbol-slice --name "<类名/方法名>"`
