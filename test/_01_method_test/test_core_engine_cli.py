#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_01_method_test/test_core_engine_cli.py
AI Reader 核心引擎 CLI（Rust ai-reader-cli）接口功能测试

引擎统一契约：CLI 与 GUI 共用 libreader_core 同一 dispatch_invoke——
同一 action 在两种宿主下结构、能力与行为完全一致。
运行前置：cargo build --release 产出 backend/target/release/ai-reader-cli。
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_BIN = WORKSPACE_ROOT / "backend" / "target" / "release" / "ai-reader-cli"


class TestCoreEngineCLI(unittest.TestCase):
    def setUp(self):
        if not CLI_BIN.exists():
            self.fail(
                "ai-reader-cli 未构建：先在 backend/ 执行 cargo build --release"
            )
        self.home = Path(tempfile.mkdtemp(prefix="ai_reader_cli_test_"))
        self.env = os.environ.copy()
        self.env["AI_READER_HOME"] = str(self.home)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def run_cli(self, args):
        res = subprocess.run(
            [str(CLI_BIN)] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
            timeout=60,
        )
        return res

    def envelope_of(self, res):
        """从 CLI 输出提取 JSON 信封（parse 子命令含人类可读前缀行）"""
        return json.loads(res.stdout[res.stdout.index("{"):])

    def test_cli_help_lists_subcommands(self):
        res = self.run_cli(["--help"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("AI Reader - Headless Core Computation", res.stdout)
        for cmd in ["parse", "books", "keywords", "graph", "mindmap", "ask", "invoke"]:
            self.assertIn(cmd, res.stdout, f"帮助应列出子命令 {cmd}")

    def test_cli_parse_books_and_invoke(self):
        # 1. 解析入库
        doc = self.home / "test_cli_doc.md"
        doc.write_text(
            "# Chapter 1\nAI Reader parses markdown into AST seamlessly.\n\n"
            "# Chapter 2\nKnowledge graph and mindmaps.",
            encoding="utf-8",
        )
        res = self.run_cli(["parse", str(doc)])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("[SUCCESS] Document parsed successfully", res.stdout)

        # 2. 书库列表（低层 invoke 直调）
        res = self.run_cli(["invoke", "--action", "book.list", "--pretty"])
        self.assertEqual(res.returncode, 0)
        envelope = self.envelope_of(res)
        self.assertEqual(envelope["code"], 0)
        titles = [b["title"] for b in envelope["data"]["books"]]
        self.assertIn("test_cli_doc", titles, f"书库应含刚解析文档: {titles}")

        # 3. H1-H6 层级：两个一级标题成两节，段落齐备
        res = self.run_cli(
            ["invoke", "--action", "book.get", "--payload", json.dumps({"book_id": 1})]
        )
        envelope = self.envelope_of(res)
        sections = envelope["data"]["sections"]
        self.assertEqual(len(sections), 2)
        for sec in sections:
            self.assertEqual(sec["level"], 1)
            self.assertTrue(sec["paragraphs"], "每个章节必须有正文段落")

    def test_cli_duplicate_parse_reports_idempotent_locate(self):
        doc = self.home / "dup.md"
        doc.write_text("# 去重样章\n唯一内容用于哈希命中。\n", encoding="utf-8")
        first = self.run_cli(["parse", str(doc)])
        self.assertEqual(first.returncode, 0)

        # 同内容重复导入：幂等定位（code=0 + duplicate=true），不再报错拦截
        second = self.run_cli(["parse", str(doc)])
        self.assertEqual(second.returncode, 0, second.stderr)
        envelope = self.envelope_of(second)
        self.assertTrue(envelope["data"]["duplicate"], "重复导入应返回 duplicate=true")
        self.assertEqual(envelope["data"]["id"], 1, "应定位到既有书目")

    def test_cli_keywords_real_scores(self):
        doc = self.home / "kw.md"
        doc.write_text(
            "# 术语\n预写式日志保证原子性。\n预写式日志保证持久性。\n\n"
            "# 其他\n快照隔离提升并发性能。\n",
            encoding="utf-8",
        )
        res = self.run_cli(["parse", str(doc)])
        self.assertEqual(res.returncode, 0)
        res = self.run_cli(["keywords", "1", "10"])
        self.assertEqual(res.returncode, 0)
        envelope = self.envelope_of(res)
        keywords = envelope["data"]["keywords"]
        self.assertTrue(keywords, "真实分词应产出关键词")
        for k in keywords:
            self.assertIn("word", k)
            self.assertIn("score", k)
            self.assertGreater(k["score"], 0.0, "TF-IDF 分数应为真实正值")

    def test_cli_mindmap_three_layers(self):
        doc = self.home / "mm.md"
        doc.write_text(
            "# 存储\n预写式日志保证原子性与持久性，日志是可靠性的基石。\n\n"
            "# 并发\n快照隔离让读事务不阻塞写事务，多版本并发控制。",
            encoding="utf-8",
        )
        res = self.run_cli(["parse", str(doc)])
        self.assertEqual(res.returncode, 0)
        res = self.run_cli(["mindmap", "1"])
        self.assertEqual(res.returncode, 0)
        envelope = self.envelope_of(res)
        nodes = envelope["data"]["nodes"]
        depths = {n["depth"] for n in nodes}
        self.assertIn(0, depths, "应有根节点")
        self.assertIn(1, depths, "应有章节分支")
        self.assertIn(2, depths, "应有章节核心词叶节点（第三层）")
        leaves = [n for n in nodes if n["depth"] == 2]
        self.assertTrue(
            all(n["label"] not in ("核心概念", "重点") for n in leaves),
            "叶节点不得再是占位串",
        )

    def test_cli_unknown_action_fails_loudly(self):
        res = self.run_cli(["invoke", "--action", "nlp.nonexistent"])
        self.assertNotEqual(res.returncode, 0, "未知 action 必须显式失败")

    def test_cli_empty_file_rejected(self):
        doc = self.home / "empty.md"
        doc.write_text("   \n", encoding="utf-8")
        res = self.run_cli(["parse", str(doc)])
        self.assertNotEqual(res.returncode, 0, "空文件必须被拦截")
        combined = res.stdout + res.stderr
        self.assertIn("为空", combined)


if __name__ == "__main__":
    unittest.main()
