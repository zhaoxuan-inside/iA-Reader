#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_03_contract_test/test_ffi_contract.py
Rust FFI 引擎 ↔ Flutter 前端 数据契约测试

背景：此前 Dart 侧契约按内存 mock 定义，全部 Flutter 测试走 mock 通道，
导致真实 libreader_core.so 与前端之间 4 处契约失配（doc.list 裸数组、
词云 action 名、词云字段、导图字段）在测试全绿的情况下静默断裂。

本测试用 ctypes 加载真实动态库，断言 FFI 输出与
frontend/lib/core/ffi/reader_engine_bridge.dart 的 mock 契约逐字段一致。
运行前置：cargo build --release 产出 backend/target/release/libreader_core.so。
"""

import ctypes
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def locate_library():
    explicit = os.environ.get("AI_READER_CONTRACT_LIB")
    if explicit:
        return Path(explicit)
    candidates = [
        WORKSPACE_ROOT / "backend" / "target" / "release" / "libreader_core.so",
        WORKSPACE_ROOT / "backend" / "target" / "debug" / "libreader_core.so",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


LIB_PATH = locate_library()


class TestFfiContract(unittest.TestCase):
    """真实动态库上的前后端契约断言

    动态库缺失时按门禁纪律硬性失败（skip 等于放过契约断裂）：
    先在 backend/ 下执行 cargo build --release。
    """

    lib = None
    tmp_home = None

    @classmethod
    def setUpClass(cls):
        if LIB_PATH is None:
            raise AssertionError(
                "libreader_core.so 未构建：先在 backend/ 执行 cargo build --release，"
                "或用 AI_READER_CONTRACT_LIB 指定动态库路径"
            )

        # SERVICE 与运行期目录均为进程级单例：必须在首次 invoke 前隔离 AI_READER_HOME
        cls.tmp_home = Path(tempfile.mkdtemp(prefix="ai_reader_contract_"))
        os.environ["AI_READER_HOME"] = str(cls.tmp_home)

        cls.lib = ctypes.CDLL(str(LIB_PATH))
        cls.lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        cls.lib.ai_reader_invoke.restype = ctypes.c_void_p
        cls.lib.ai_reader_free_string.argtypes = [ctypes.c_void_p]
        cls.lib.ai_reader_free_string.restype = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_home, ignore_errors=True)

    def invoke(self, action, payload):
        """调用 C-ABI 并解析六元组信封，返回 (code, data, message)"""
        ptr = self.lib.ai_reader_invoke(
            action.encode("utf-8"), json.dumps(payload).encode("utf-8")
        )
        self.assertIsNotNone(ptr, "ai_reader_invoke 返回空指针")
        raw = ctypes.string_at(ptr)
        self.lib.ai_reader_free_string(ptr)
        envelope = json.loads(raw.decode("utf-8"))
        self.assertIn("code", envelope)
        self.assertIn("message", envelope)
        self.assertIn("data", envelope)
        return envelope["code"], envelope["data"], envelope["message"]

    _import_counter = 0

    def _import_sample_book(self):
        """导入一篇三章节样例书（内容唯一，规避同哈希去重），返回 (book_id, md_path)"""
        TestFfiContract._import_counter += 1
        n = TestFfiContract._import_counter
        md = self.tmp_home / f"contract_sample_{n}.md"
        md.write_text(
            f"# 第{n}章 边界\n"
            f"边界决定系统的形状，接口是边界上的协议。样例{n}。\n\n"
            f"# 第{n}章续 深模块\n"
            f"深模块以少量接口封装大量实现，读者无需理解内部细节。样例{n}。\n\n"
            f"# 第{n}章末 一致性\n"
            f"单一事实源消除同名异义，契约测试消除静默漂移。样例{n}。\n",
            encoding="utf-8",
        )
        code, data, msg = self.invoke("doc.parse", {"file_path": str(md)})
        self.assertEqual(code, 0, f"doc.parse 失败: {msg}")
        return data["id"], md

    def test_duplicate_import_rejected(self):
        book_id, md = self._import_sample_book()
        code, _, msg = self.invoke("doc.parse", {"file_path": str(md)})
        self.assertNotEqual(code, 0, "同内容重复导入必须被拦截（FEAT-001 去重）")
        self.assertIn("已在书库", msg)
        # 原书不受影响
        code, doc, _ = self.invoke("doc.get", {"book_id": book_id})
        self.assertEqual(code, 0)
        self.assertEqual(len(doc["sections"]), 3)

    # ------------------------------------------------------------------
    # 契约 1：doc.list 必须返回信封 Map（data['books']），且章节计数真实
    # 前端消费点：library_screen.dart _loadBooks 取 res.data['books']
    # ------------------------------------------------------------------
    def test_doc_list_returns_books_map_with_section_counts(self):
        book_id, _ = self._import_sample_book()

        code, data, msg = self.invoke("doc.list", {})
        self.assertEqual(code, 0, f"doc.list 失败: {msg}")
        self.assertIsInstance(
            data, dict, "doc.list 的 data 必须是 Map（裸数组会令前端信封解析抛错并静默回退 mock）"
        )
        books = data.get("books")
        self.assertIsInstance(books, list, "doc.list 缺少 books 数组字段")
        self.assertTrue(any(b["id"] == book_id for b in books), "刚导入的书未出现在书库列表")
        for b in books:
            self.assertIn("title", b)
            self.assertIn("format", b)
            self.assertIn("sections_count", b, "书库行需要真实章节数（前端显示 'N 个章节'）")
            self.assertIsInstance(b["sections_count"], int)

        sample = next(b for b in books if b["id"] == book_id)
        self.assertEqual(sample["sections_count"], 3, "三章节样例书的章节数应为 3")

    # ------------------------------------------------------------------
    # 契约 2：词云 action 名与字段形状
    # 前端消费点：main.dart 调 'nlp.keyword_extract'，读 word/score/count
    # ------------------------------------------------------------------
    def test_keyword_extract_action_and_fields(self):
        book_id, _ = self._import_sample_book()

        # action 名必须是前端注册的 nlp.keyword_extract（引擎须兼容此名）
        code, data, msg = self.invoke("nlp.keyword_extract", {"book_id": book_id, "top_n": 10})
        self.assertEqual(code, 0, f"nlp.keyword_extract 必须可用（前端唯一下单名）: {msg}")
        keywords = data.get("keywords")
        self.assertIsInstance(keywords, list)
        self.assertTrue(keywords, "关键词列表不应为空")
        for k in keywords:
            self.assertIn("word", k)
            self.assertIn("score", k, "词云字号映射依赖 score 字段（Rust 原生 tfidf_score 前端读不到）")
            self.assertIn("count", k, "词云依赖 count 字段（Rust 原生 frequency 前端读不到）")
            self.assertIsInstance(k["score"], (int, float))
            self.assertIsInstance(k["count"], int)

    # ------------------------------------------------------------------
    # 契约 3：导图节点字段形状
    # 前端消费点：main.dart _loadDocumentData 读 label/depth/parent_id/section_id
    # ------------------------------------------------------------------
    def test_mindmap_generate_node_fields(self):
        book_id, _ = self._import_sample_book()

        code, data, msg = self.invoke("mindmap.generate", {"book_id": book_id})
        self.assertEqual(code, 0, f"mindmap.generate 失败: {msg}")
        nodes = data.get("nodes")
        self.assertIsInstance(nodes, list)
        self.assertTrue(nodes, "导图节点不应为空")
        for n in nodes:
            self.assertIn("id", n)
            self.assertIn("label", n, "导图节点字段名必须是 label（Rust 原生 title 前端读不到）")
            self.assertIn("depth", n, "导图节点字段名必须是 depth（Rust 原生 level 前端读不到）")
            self.assertIsInstance(n["depth"], int)
            self.assertIn("parent_id", n)
            self.assertIn("section_id", n)
        root = next(n for n in nodes if n["parent_id"] is None)
        self.assertTrue(root["label"], "根节点 label 不得为空串")
        self.assertEqual(root["depth"], 0)
        # 章节节点须携带 section_id 供点击跳转
        with_section = [n for n in nodes if n["section_id"] is not None]
        self.assertTrue(with_section, "章节导图节点必须携带 section_id 才能联动章节跳转")

    # ------------------------------------------------------------------
    # 契约 4：解析器诚实化
    # MVP 冻结范围：仅 Markdown/TXT；PDF/EPUB 必须显式拒绝，禁止返回假正文
    # ------------------------------------------------------------------
    def test_unsupported_format_rejected_not_fabricated(self):
        fake_pdf = self.tmp_home / "fake_paper.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake binary payload \xff\xff")

        code, data, msg = self.invoke("doc.parse", {"file_path": str(fake_pdf)})
        self.assertNotEqual(code, 0, "PDF 解析必须失败返回，禁止静默产出硬编码假正文")
        self.assertIn("支持", msg, "错误信息应说明当前支持的格式")

    def test_md_parse_produces_real_metadata(self):
        md = self.tmp_home / "hash_check.md"
        md.write_text("# 标题甲\n正文内容一。\n\n# 标题乙\n正文内容二。\n", encoding="utf-8")

        code, data, msg = self.invoke("doc.parse", {"file_path": str(md)})
        self.assertEqual(code, 0, f"doc.parse 失败: {msg}")
        self.assertRegex(data["file_hash"], r"^[0-9a-f]{64}$", "file_hash 必须是真实 SHA-256")
        self.assertGreater(data["total_pages"], 0)

        code, doc, msg = self.invoke("doc.get", {"book_id": data["id"]})
        self.assertEqual(code, 0)
        sections = doc["sections"]
        self.assertEqual(len(sections), 2, "两个一级标题应切分为两个章节")
        for sec in sections:
            self.assertTrue(sec["title"].startswith("标题"), "章节标题应来自 Markdown 标题")
            self.assertTrue(sec["paragraphs"], "每个章节必须有正文段落")

    # ------------------------------------------------------------------
    # 契约 5：信封错误路径——未知 action 必须显式报错
    # ------------------------------------------------------------------
    def test_unknown_action_explicit_error(self):
        code, data, msg = self.invoke("nlp.nonexistent_action", {})
        self.assertNotEqual(code, 0)
        self.assertIn("Unknown action", msg)
        self.assertIsNone(data)


if __name__ == "__main__":
    unittest.main()
