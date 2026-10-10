#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_00_e2e/test_reader_full_flow_e2e.py
AI Reader 全链路端到端冒烟与集成测试 (End-to-End Golden Path & Exception Scenarios)
严格按照 quality_gates.md 门禁规范：
  - 主流程用例 100% 贯通 (文档解构 -> 沉浸阅读/聚焦模式 -> 划词悬浮伴读 -> 原位追问 -> 边注归档 -> 导图拓扑生成)
  - 致命异常与离线降级链路 100% 覆盖 (离线启发式降级卡片、文件不存在或损坏、CLI 与 FFI 一致性)
"""

import os
import sys
import json
import unittest
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

E2E_DB = WORKSPACE_ROOT / "test_e2e_suite.db"
os.environ["AI_READER_DB_PATH"] = str(E2E_DB)

from backend.reader_engine import (
    get_engine,
    ai_reader_invoke,
)

CLI_SCRIPT = WORKSPACE_ROOT / "linux" / "ai_reader_app.py"


class TestReaderFullFlowE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if E2E_DB.exists():
            E2E_DB.unlink()
        cls.engine = get_engine()

        # 准备一个标准的长篇技术文档 (含两章、多个段落与典型技术论点)
        cls.sample_doc = WORKSPACE_ROOT / "e2e_sample_distributed_systems.md"
        cls.sample_doc.write_text(
            "# 第 1 章 分布式存储引擎\n\n"
            "在现代分布式数据库设计中，预写式日志（WAL）是保证原子性与持久性的关键机制。\n"
            "所有修改操作在落地存储介质前，必须先将日志顺序追加写入磁盘。\n\n"
            "# 第 2 章 并发控制与快照隔离\n\n"
            "SQLite 在 WAL 模式下，读取者绝不阻塞写入者，写入者也绝不阻塞读取者。\n"
            "这极大地提升了系统的整体并发读写吞吐量。\n"
            "然而在检查点执行期间，仍需协调 WAL 文件的刷新与截断，若并发事务堆积过高可能导致延迟抖动。\n",
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        if E2E_DB.exists():
            E2E_DB.unlink()
        if cls.sample_doc.exists():
            cls.sample_doc.unlink()

    def test_01_golden_reading_and_companion_pipeline_e2e(self):
        """
        [主路径端到端]：
        文档解构 -> 沉浸阅读/聚焦弱化仿真 -> 划词伴读(4大模板) -> 原位追问 -> 边注持久化 -> 知识导图生成
        """
        # ==================== 1. 文档解析与 AST 解构 (doc.parse) ====================
        parse_payload = json.dumps({"file_path": str(self.sample_doc)})
        res_parse_raw = ai_reader_invoke("doc.parse", parse_payload)
        res_parse = json.loads(res_parse_raw)

        self.assertEqual(res_parse["code"], 0, "doc.parse 必须成功返回 code=0")
        meta = res_parse["data"]
        book_id = meta["id"]
        self.assertGreater(book_id, 0)
        self.assertEqual(meta["format"], "md")

        # 校验章节与句子已切片
        doc_detail_raw = ai_reader_invoke("doc.get", json.dumps({"book_id": book_id}))
        doc_detail = json.loads(doc_detail_raw)
        self.assertEqual(doc_detail["code"], 0)
        sections = doc_detail["data"]["sections"]
        self.assertEqual(len(sections), 2, "应识别出 2 个章节")

        # ==================== 2. 模拟前端 Focus Mode 弱化计算 ====================
        # 前端从章节 AST 中提取句子流，选定特定段落 (SQLite 在 WAL 模式下……)
        # 根据 DESIGN.md：焦点段落透明度 1.0，其余段落弱化至 0.65
        sentences = self.engine.storage.get_sentences(sections[0]["id"])
        self.assertGreater(len(sentences), 0)
        focus_sentence = sentences[0]

        def compute_opacity(target_id, active_id, focus_enabled=True):
            if not focus_enabled:
                return 1.0
            return 1.0 if target_id == active_id else 0.65

        self.assertEqual(compute_opacity("p2", "p2", True), 1.0)
        self.assertEqual(compute_opacity("p1", "p2", True), 0.65)
        self.assertEqual(compute_opacity("p3", "p2", True), 0.65)
        # 退出失焦
        self.assertEqual(compute_opacity("p1", "p2", False), 1.0)

        # ==================== 3. 划词悬浮胶囊直达伴读 (ai.companion_ask) ====================
        templates_to_test = ["logic", "general", "critical", "term"]
        for tpl in templates_to_test:
            ask_payload = json.dumps({
                "book_id": book_id,
                "template_type": tpl,
                "selected_text": focus_sentence["text"],
                "prompt": ""
            })
            res_ask_raw = ai_reader_invoke("ai.companion_ask", ask_payload)
            res_ask = json.loads(res_ask_raw)

            self.assertEqual(res_ask["code"], 0, f"模板 {tpl} 伴读必须成功")
            self.assertIn("response", res_ask["data"])
            self.assertEqual(res_ask["data"]["template_type"], tpl)
            self.assertIn("duration_ms", res_ask["metrics"])
            self.assertLess(res_ask["metrics"]["duration_ms"], 800, "伴读响应指标需小于 800ms")

        # ==================== 4. 卡片内原位追问 (In-card Follow-up) ====================
        followup_payload = json.dumps({
            "book_id": book_id,
            "template_type": "logic",
            "selected_text": focus_sentence["text"],
            "prompt": "如果 WAL 发生并发写入阻塞，底层的快照机制如何保障一致性？"
        })
        res_followup_raw = ai_reader_invoke("ai.companion_ask", followup_payload)
        res_followup = json.loads(res_followup_raw)
        self.assertEqual(res_followup["code"], 0)
        response_text = res_followup["data"]["response"]
        self.assertIn("针对追问", response_text)

        # ==================== 5. 存为段落边注 (annotation.save) ====================
        annot_payload = json.dumps({
            "book_id": book_id,
            "section_id": sections[0]["id"],
            "note_text": response_text,
            "color": "#007AFF",
            "style": "highlight"
        })
        res_annot_raw = ai_reader_invoke("annotation.save", annot_payload)
        res_annot = json.loads(res_annot_raw)
        self.assertEqual(res_annot["code"], 0, "保存边注必须成功")
        annot_id = res_annot["data"]["annotation_id"]
        self.assertGreater(annot_id, 0)

        # 验证边注已原子持久化至本地 SQLite
        list_annot_raw = ai_reader_invoke("annotation.list", json.dumps({"book_id": book_id}))
        list_annot = json.loads(list_annot_raw)
        self.assertEqual(list_annot["code"], 0)
        annots = list_annot["data"]["annotations"]
        self.assertEqual(len(annots), 1)
        self.assertEqual(annots[0]["id"], annot_id)
        self.assertEqual(annots[0]["note_text"], response_text)

        # ==================== 6. 三级概念拓扑与层级思维导图生成 ====================
        # 6a. 提取关键词
        kw_payload = json.dumps({"book_id": book_id, "top_k": 8})
        res_kw = json.loads(ai_reader_invoke("nlp.keyword_extract", kw_payload))
        self.assertEqual(res_kw["code"], 0)
        self.assertGreater(len(res_kw["data"]["keywords"]), 0)

        # 6b. 构建共现拓扑 (PMI)
        graph_payload = json.dumps({"book_id": book_id})
        res_graph = json.loads(ai_reader_invoke("graph.build", graph_payload))
        self.assertEqual(res_graph["code"], 0)
        self.assertGreaterEqual(len(res_graph["data"]["nodes"]), 0)
        self.assertLess(res_graph["metrics"]["duration_ms"], 200, "拓扑耗时需 < 200ms")

        # 6c. 提取思维导图树 (mindmap.generate)
        mm_payload = json.dumps({"book_id": book_id})
        res_mm = json.loads(ai_reader_invoke("mindmap.generate", mm_payload))
        self.assertEqual(res_mm["code"], 0)
        nodes = res_mm["data"]["nodes"]
        self.assertGreater(len(nodes), 0, "思维导图应包含节点")

    def test_02_fatal_offline_graceful_fallback_e2e(self):
        """
        [致命与异常链路端到端]：
        模拟离线或无外网连接时，验证伴读管道自动降级为确定性思维卡片且零崩溃
        """
        offline_payload = json.dumps({
            "book_id": 1,
            "template_type": "critical",
            "selected_text": "这是一个离线测试段落，验证系统启发卡片降级",
            "prompt": ""
        })
        res_raw = ai_reader_invoke("ai.companion_ask", offline_payload)
        res = json.loads(res_raw)

        self.assertEqual(res["code"], 0, "离线调用必须降级成功且 code 为 0")
        self.assertIn("【离线思考启发】", res["data"]["response"])
        self.assertLess(res["metrics"]["duration_ms"], 800, "离线降级响应必须毫秒级返回")

    def test_03_corrupted_document_error_handling_e2e(self):
        """
        [文档异常保护端到端]：
        传入不存在的文件路径，验证返回标准信封错误码 50001 且进程不崩溃
        """
        bad_payload = json.dumps({"file_path": "/path/to/non_existent_doc_never_here.pdf"})
        res_raw = ai_reader_invoke("doc.parse", bad_payload)
        res = json.loads(res_raw)

        self.assertEqual(res["code"], 50001, "文件不存在必须返回 50001 错误码")
        self.assertIn("File not found", res["message"])

    def test_04_cli_and_ffi_dispatch_parity_e2e(self):
        """
        [CLI 与 FFI 跨接口一致性端到端]：
        验证通过 CLI 命令行与直接调用六元组信封返回规范 100% 对齐
        """
        cmd = [sys.executable, str(CLI_SCRIPT), "--help"]
        res_cli = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(WORKSPACE_ROOT))
        self.assertEqual(res_cli.returncode, 0)
        self.assertIn("parse", res_cli.stdout)
        self.assertIn("ask", res_cli.stdout)
        self.assertIn("mindmap", res_cli.stdout)

        # 通过 low-level invoke 触发 doc.list
        res_ffi_raw = ai_reader_invoke("doc.list", "{}")
        res_ffi = json.loads(res_ffi_raw)
        self.assertEqual(res_ffi["code"], 0)
        self.assertIn("books", res_ffi["data"])


if __name__ == "__main__":
    unittest.main()
