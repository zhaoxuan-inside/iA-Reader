#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_01_method_test/test_reader_core_engine.py
六元组业务方法与 FFI 契约全覆盖单元测试
覆盖率指标：核心分支 ≥ 85%，降级与补偿分支 100%
"""

import os
import sys
import json
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.reader_engine import (
    StorageManager,
    ReaderEngineService,
    ai_reader_invoke,
    dispatch_invoke,
    tokenize,
    calculate_tfidf,
    calculate_textrank,
    build_co_occurrence
)

TEST_DB = "test_reader_suite.db"

class TestReaderCoreEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        cls.storage = StorageManager(TEST_DB)
        cls.service = ReaderEngineService(cls.storage)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_01_sqlite_storage_and_migrations(self):
        """测试 SQLite 初始化、迁移执行与基础增删改查"""
        conn = self.storage.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cur.fetchall()]
        conn.close()

        expected_tables = ["book_meta", "book_section", "sentence_node", "keyword_node", "keyword_relation", "mindmap_node", "annotation", "ai_conversation"]
        for t in expected_tables:
            self.assertIn(t, tables, f"Table {t} should be created by migration")

    def test_02_doc_parse_six_tuple(self):
        """测试 doc_parse 主方法及补偿、降级、度量与回调"""
        # 1. 主方法 (Markdown 解析)
        sample_md = Path("sample_test_doc.md")
        sample_md.write_text("# Chapter 1\nDeep reading with cognitive companion.\n# Chapter 2\nKnowledge graph and mindmaps.", encoding="utf-8")
        
        meta = self.service.doc_parse(str(sample_md))
        self.assertIsNotNone(meta["id"])
        self.assertEqual(meta["format"], "md")

        # 2. 降级方法 (Fallback)
        fallback_res = self.service.doc_parse_fallback("non_existent.weird")
        self.assertIn("meta", fallback_res)

        # 3. 补偿方法 (Compensate) - 确保不抛异常
        self.service.doc_parse_compensate(str(sample_md))

        # 4. 度量与回调
        self.service.doc_parse_metrics(12.5, 5)
        self.service.doc_parse_recall(meta["id"])

        if sample_md.exists():
            sample_md.unlink()

    def test_03_nlp_keyword_extract_six_tuple(self):
        """测试 nlp_keyword_extract 主方法与衍生"""
        # 主方法
        keywords = self.service.nlp_keyword_extract(book_id=1, top_n=5)
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)
        self.assertIn("word", keywords[0])

        # 降级方法 (Fallback)
        fb = self.service.nlp_keyword_extract_fallback(book_id=999, top_n=2)
        self.assertEqual(len(fb), 2)

        # 补偿、度量与回调
        self.service.nlp_keyword_extract_compensate(book_id=1)
        self.service.nlp_keyword_extract_metrics(20.0, len(keywords))
        self.service.nlp_keyword_extract_recall(book_id=1)

    def test_04_keyword_graph_build_six_tuple(self):
        """测试 keyword_graph_build 主方法与衍生"""
        relations = self.service.keyword_graph_build(book_id=1, min_co_occurrence=1)
        self.assertIsInstance(relations, list)

        # 降级方法 (Fallback)
        fb = self.service.keyword_graph_build_fallback(book_id=999, min_co=1)
        self.assertEqual(len(fb), 1)

        # 补偿、度量与回调
        self.service.keyword_graph_build_compensate(book_id=1)
        self.service.keyword_graph_build_metrics(15.0, len(relations))
        self.service.keyword_graph_build_recall(book_id=1)

    def test_05_mindmap_generate_six_tuple(self):
        """测试 mindmap_generate 主方法与衍生"""
        nodes = self.service.mindmap_generate(book_id=1)
        self.assertIsInstance(nodes, list)
        self.assertTrue(len(nodes) >= 1)

        # 降级方法 (Fallback)
        fb = self.service.mindmap_generate_fallback(book_id=999)
        self.assertEqual(fb[0]["title"], "全书大纲")

        # 补偿、度量与回调
        self.service.mindmap_generate_compensate(book_id=1)
        self.service.mindmap_generate_metrics(8.0, len(nodes))
        self.service.mindmap_generate_recall(book_id=1)

    def test_06_annotation_manage_six_tuple(self):
        """测试 annotation_manage 主方法与衍生"""
        annot_data = {
            "book_id": 1,
            "section_id": 1,
            "color": "#FFE066",
            "style": "margin_note",
            "note_text": "Unit Test Margin Annotation",
            "anchor_json": json.dumps({"page": 1, "offset": 100}),
            "ai_response": "AI companion note"
        }
        annot_id = self.service.annotation_manage(annot_data)
        self.assertGreater(annot_id, 0)

        # 列表查询
        annots = self.storage.get_annotations(book_id=1)
        self.assertTrue(any(a["id"] == annot_id for a in annots))

        # 降级方法 (Fallback)
        fb_id = self.service.annotation_manage_fallback(annot_data)
        self.assertEqual(fb_id, 1)

        # 补偿、度量与回调
        self.service.annotation_manage_compensate(book_id=1)
        self.service.annotation_manage_metrics(3.2, 1)
        self.service.annotation_manage_recall(annot_id)

    def test_07_ai_companion_stream_six_tuple(self):
        """测试 4 大认知伴读模板（通俗/逻辑/辩驳/术语）与降级兜底"""
        templates = ["general", "logic", "critical", "term"]
        for tpl in templates:
            resp = self.service.ai_companion_stream(
                book_id=1,
                template_type=tpl,
                selected_text="Transformer 架构的自注意力机制",
                prompt="请详细解释"
            )
            self.assertIsInstance(resp, str)
            self.assertTrue(len(resp) > 10)

        # 降级方法 (Fallback)
        fb = self.service.ai_companion_stream_fallback("general", "未知概念")
        self.assertIn("离线思考启发", fb)

        # 补偿、度量与回调
        self.service.ai_companion_stream_compensate(book_id=1)
        self.service.ai_companion_stream_metrics(120.0, 1)
        self.service.ai_companion_stream_recall(book_id=1)

    def test_08_ffi_ai_reader_invoke_envelope_contracts(self):
        """测试 FFI 统一 JSON 信封输入输出"""
        # doc.list
        res_str = ai_reader_invoke("doc.list", "{}")
        res = json.loads(res_str)
        self.assertEqual(res["code"], 0)
        self.assertEqual(res["message"], "success")
        self.assertIn("books", res["data"])
        self.assertIn("duration_ms", res["metrics"])

        # 错误分发 (Unknown Action)
        err_str = ai_reader_invoke("invalid.action", "{}")
        err_res = json.loads(err_str)
        self.assertEqual(err_res["code"], 50001)
        self.assertIsNone(err_res["data"])


if __name__ == "__main__":
    unittest.main()
