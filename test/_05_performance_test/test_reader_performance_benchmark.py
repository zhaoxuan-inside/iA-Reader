#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_05_performance_test/test_reader_performance_benchmark.py
AI Reader 性能基准与 SLA 验证（真实 libreader_core.so，ctypes 直调 C-ABI）

按 phased_plan §1 的 MVP 成功指标：
  - 10 万字文档冷启动解构（book.parse）< 1500ms
  - 离线 NLP（关键词/图谱/导图）< 200ms/项
  - 离线启发伴读卡片（api_key 未配置）< 10ms
此前基准指向已移除的 Python 引擎，性能承诺无工程载体——本版基准与
生产 GUI 走完全相同的动态库与信封路径。
"""

import ctypes
import json
import os
import shutil
import tempfile
import time
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


class TestReaderPerformanceBenchmark(unittest.TestCase):
    lib = None
    home = None

    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp(prefix="ai_reader_perf_"))
        os.environ["AI_READER_HOME"] = str(cls.home)
        cls.lib = ctypes.CDLL(str(LIB_PATH))
        cls.lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        cls.lib.ai_reader_invoke.restype = ctypes.c_void_p
        cls.lib.ai_reader_free_string.argtypes = [ctypes.c_void_p]
        cls.lib.ai_reader_free_string.restype = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    def invoke(self, action, payload):
        ptr = self.lib.ai_reader_invoke(
            action.encode("utf-8"), json.dumps(payload).encode("utf-8")
        )
        raw = ctypes.string_at(ptr)
        self.lib.ai_reader_free_string(ptr)
        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def build_large_markdown(target_chars: int) -> Path:
        """构造约 target_chars 字的分层 Markdown 长文（章节/段落/术语复现）"""
        section_tpl = (
            "# 章节廿三：分布式存储的第 {i} 个侧面\n\n"
            "预写式日志在第 {i} 层保证了事务的原子性与持久性，"
            "快照隔离让多版本并发控制下的读事务不阻塞写事务。\n\n"
            "检查点机制在第 {i} 层平衡了日志截断与恢复时延，"
            "一致性哈希把数据分布的抖动限制在环上的相邻节点之间。\n\n"
        )
        parts = []
        total = 0
        i = 0
        while total < target_chars:
            parts.append(section_tpl.format(i=i))
            total += len(section_tpl.format(i=i))
            i += 1
        path = Path(tempfile.mkdtemp(prefix="ai_reader_perf_doc_")) / "large_doc.md"
        path.write_text("".join(parts), encoding="utf-8")
        return path

    def test_01_large_doc_cold_parse_under_1500ms(self):
        """10 万字文档冷启动解构 < 1500ms（phased_plan §1 SLA-1）"""
        doc = self.build_large_markdown(100_000)
        size = doc.stat().st_size
        start = time.perf_counter()
        env = self.invoke("book.parse", {"file_path": str(doc)})
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(env["code"], 0, env["message"])
        self.assertLess(
            elapsed_ms, 1500,
            f"10 万字冷启动解构 {elapsed_ms:.0f}ms 超出 1500ms SLA（文档 {size} 字节）",
        )
        book_id = env["data"]["id"]
        print(f"\n[PERF] book.parse 10万字: {elapsed_ms:.1f}ms (book_id={book_id})")

    def test_02_offline_nlp_under_200ms_each(self):
        """关键词/图谱/导图 离线 NLP 各 < 200ms（SLA-2）"""
        doc = self.build_large_markdown(100_000)
        env = self.invoke("book.parse", {"file_path": str(doc)})
        self.assertEqual(env["code"], 0)
        book_id = env["data"]["id"]

        for action, payload in [
            ("nlp.keyword_extract", {"book_id": book_id, "top_n": 30}),
            ("nlp.build_graph", {"book_id": book_id, "min_co_occurrence": 2}),
            ("mindmap.generate", {"book_id": book_id}),
        ]:
            start = time.perf_counter()
            env = self.invoke(action, payload)
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.assertEqual(env["code"], 0, f"{action}: {env['message']}")
            self.assertLess(
                elapsed_ms, 200,
                f"{action} 耗时 {elapsed_ms:.0f}ms 超出 200ms SLA",
            )
            print(f"\n[PERF] {action}: {elapsed_ms:.1f}ms")

    def test_03_offline_companion_card_under_10ms(self):
        """离线启发伴读卡片 < 10ms（api_key 未配置，SLA-3 降级路径）"""
        # 该测试进程独立 AI_READER_HOME：未配置过密钥 → 直接走离线
        start = time.perf_counter()
        env = self.invoke("ai.companion_ask", {
            "book_id": 0,
            "template_type": "general",
            "selected_text": "预写式日志的原子性保证",
            "prompt": "",
        })
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(env["code"], 0)
        self.assertIn("【离线模式】", env["data"]["response"], "未配置密钥应走离线卡片")
        self.assertLess(elapsed_ms, 10, f"离线卡片 {elapsed_ms:.1f}ms 超出 10ms SLA")
        print(f"\n[PERF] offline companion card: {elapsed_ms:.2f}ms")


if __name__ == "__main__":
    unittest.main(verbosity=2)
