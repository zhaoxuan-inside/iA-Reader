#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_02_integration_test/test_cross_action_integration.py
跨 action 数据流集成测试（真实 libreader_core.so，ctypes 直调 C-ABI）

与 _03_contract_test（信封形状）和 _00_e2e（主旅程）互补，此处聚焦
跨 action 的数据一致性：
  1. book.parse 产出的段落 id 与 annotation.save 锚点真实可绑定
  2. progress.save → book.get → progress.get 续读锚点逐字段一致
  3. annotation.updated / deleted 与 annotation.list 状态机一致
  4. book.deleted 级联清理后，progress/标注/段落全部不可达
  5. 新进程句柄（模拟重启）读回全部持久化状态
"""

import ctypes
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def locate_library():
    candidates = [
        WORKSPACE_ROOT / "backend" / "target" / "release" / "libreader_core.so",
        WORKSPACE_ROOT / "backend" / "target" / "debug" / "libreader_core.so",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise AssertionError("libreader_core.so 未构建：先在 backend/ 执行 cargo build --release")


LIB_PATH = locate_library()


class CrossActionIntegration(unittest.TestCase):
    home = None

    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp(prefix="ai_reader_integration_"))
        os.environ["AI_READER_HOME"] = str(cls.home)
        cls.lib = cls._load()
        # 样例书：两章各两段
        doc = cls.home / "integration_sample.md"
        doc.write_text(
            "# 甲章\n甲章第一段，讲述预写式日志。\n\n甲章第二段，讲述快照隔离。\n\n"
            "# 乙章\n乙章第一段，讲述一致性哈希。\n\n乙章第二段，讲述检查点机制。\n",
            encoding="utf-8",
        )
        env = cls.invoke(cls.lib, "book.parse", {"file_path": str(doc)})
        assert env["code"] == 0, env["message"]
        cls.book_id = env["data"]["id"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    @staticmethod
    def _load():
        lib = ctypes.CDLL(str(LIB_PATH))
        lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.ai_reader_invoke.restype = ctypes.c_void_p
        lib.ai_reader_free_string.argtypes = [ctypes.c_void_p]
        lib.ai_reader_free_string.restype = None
        return lib

    @classmethod
    def invoke(cls, lib, action, payload):
        ptr = lib.ai_reader_invoke(
            action.encode("utf-8"), json.dumps(payload).encode("utf-8")
        )
        raw = ctypes.string_at(ptr)
        lib.ai_reader_free_string(ptr)
        return json.loads(raw.decode("utf-8"))

    def invoke_ok(self, action, payload):
        env = self.invoke(self.lib, action, payload)
        self.assertEqual(env["code"], 0, f"{action}: {env['message']}")
        return env["data"]

    # ------------------------------------------------------------------
    def test_01_paragraphs_boundable_by_annotations(self):
        """解析产出的段落 id 必须能被标注锚点真实绑定（列表回读一致）"""
        doc = self.invoke_ok("book.get", {"book_id": self.book_id})
        first_para = doc["sections"][0]["paragraphs"][0]
        self.assertIn("预写式日志", first_para["text"])

        saved = self.invoke_ok("annotation.save", {
            "book_id": self.book_id,
            "section_id": doc["sections"][0]["id"],
            "style": "highlight",
            "color": "#CA8A04",
            "origin": "manual",
            "anchor": {
                "paragraph_id": first_para["id"],
                "section_id": doc["sections"][0]["id"],
                "start": 0,
                "end": 6,
            },
        })
        rows = self.invoke_ok("annotation.list", {"book_id": self.book_id})["annotations"]
        hit = next(a for a in rows if a["id"] == saved["annotation_id"])
        anchor = json.loads(hit["anchor_json"]) if isinstance(hit["anchor_json"], str) else hit["anchor_json"]
        self.assertEqual(anchor["paragraph_id"], first_para["id"],
                         "标注锚点必须指向真实存在的段落 id")
        self.assertEqual(hit["origin"], "manual")

    def test_02_progress_roundtrip_fields(self):
        """progress.save → book.get / progress.get 续读锚点逐字段一致"""
        doc = self.invoke_ok("book.get", {"book_id": self.book_id})
        last_section = doc["sections"][-1]
        self.invoke_ok("progress.save", {
            "book_id": self.book_id,
            "section_id": last_section["id"],
            "paragraph_index": 3,
            "char_offset": 7,
            "progress": 0.75,
        })
        prog = self.invoke_ok("progress.get", {"book_id": self.book_id})
        self.assertEqual(prog["read_section_id"], last_section["id"])
        self.assertEqual(prog["read_paragraph_index"], 3)
        self.assertEqual(prog["read_char_offset"], 7)
        self.assertAlmostEqual(prog["read_progress"], 0.75)

        meta = self.invoke_ok("book.get", {"book_id": self.book_id})["meta"]
        self.assertEqual(meta["read_paragraph_index"], 3, "book.get 的 meta 应携带续读锚点")
        self.assertIsNotNone(meta["last_read_at"])

    def test_03_annotation_lifecycle_state_machine(self):
        """updated 部分更新 / deleted 软删 → list 状态一致（自建自删，不依赖其他用例）"""
        created = self.invoke_ok("annotation.save", {
            "book_id": self.book_id,
            "style": "underline",
            "color": "#007AFF",
            "origin": "manual",
            "anchor": {"paragraph_id": "p_lifecycle", "start": 0, "end": 4},
        })
        target = created["annotation_id"]

        upd = self.invoke_ok("annotation.updated", {
            "annotation_id": target,
            "note_text": "集成更新后的批注",
        })
        self.assertEqual(upd["status"], "updated")
        rows = self.invoke_ok("annotation.list", {"book_id": self.book_id})["annotations"]
        hit = next(a for a in rows if a["id"] == target)
        self.assertEqual(hit["note_text"], "集成更新后的批注")

        self.invoke_ok("annotation.deleted", {"annotation_id": target})
        rows = self.invoke_ok("annotation.list", {"book_id": self.book_id})["annotations"]
        self.assertFalse(any(a["id"] == target for a in rows), "软删后列表不得再出现")

    def test_04_book_delete_cascades_everything(self):
        """删除书籍后：书库/章节/标注/进度全部不可达，重复删除显式报错"""
        # 建一本独立样书用于级联验证
        doc_path = self.home / "cascade_sample.md"
        doc_path.write_text("# 级联样章\n级联删除验证内容。\n", encoding="utf-8")
        env = self.invoke(self.lib, "book.parse", {"file_path": str(doc_path)})
        self.assertEqual(env["code"], 0)
        bid = env["data"]["id"]

        self.invoke_ok("annotation.save", {
            "book_id": bid, "style": "margin_note",
            "note_text": "随书清理", "anchor": {"paragraph_id": "p1"},
        })
        self.invoke_ok("progress.save", {
            "book_id": bid, "section_id": None, "paragraph_index": 0,
            "char_offset": 0, "progress": 0.5,
        })

        self.assertEqual(
            self.invoke_ok("book.deleted", {"book_id": bid})["status"], "deleted")
        self.assertEqual(
            self.invoke_ok("book.get", {"book_id": bid})["sections"], [])
        self.assertEqual(
            self.invoke_ok("annotation.list", {"book_id": bid})["annotations"], [])
        env = self.invoke(self.lib, "progress.get", {"book_id": bid})
        self.assertNotEqual(env["code"], 0, "删除后 progress.get 必须显式报错")
        env = self.invoke(self.lib, "book.deleted", {"book_id": bid})
        self.assertNotEqual(env["code"], 0, "重复删除必须显式报错")

    def test_05_new_process_handle_reads_back_state(self):
        """新 CDLL 实例（模拟应用重启）：书库/标注/进度全部持久可读"""
        fresh = self._load()
        env = self.invoke(fresh, "book.list", {})
        self.assertEqual(env["code"], 0)
        books = env["data"]["books"]
        self.assertTrue(any(b["id"] == self.book_id for b in books))

        env = self.invoke(fresh, "progress.get", {"book_id": self.book_id})
        self.assertEqual(env["code"], 0)
        self.assertEqual(env["data"]["read_paragraph_index"], 3, "续读锚点跨进程保持")

        rows = self.invoke(fresh, "annotation.list", {"book_id": self.book_id})["data"]["annotations"]
        self.assertTrue(rows, "标注跨进程保持")


if __name__ == "__main__":
    unittest.main()
