#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_01_method_test/test_core_engine_cli.py
AI Reader 核心计算与解析引擎 CLI 接口功能测试
"""

import sys
import json
import unittest
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_SCRIPT = WORKSPACE_ROOT / "linux" / "ai_reader_app.py"


class TestCoreEngineCLI(unittest.TestCase):
    def run_cli(self, args):
        cmd = [sys.executable, str(CLI_SCRIPT)] + args
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(WORKSPACE_ROOT))
        return res

    def test_cli_help(self):
        res = self.run_cli(["--help"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("AI Reader - Headless Core Computation & Document Parsing Engine CLI", res.stdout)
        self.assertIn("parse", res.stdout)
        self.assertIn("keywords", res.stdout)
        self.assertIn("graph", res.stdout)
        self.assertIn("mindmap", res.stdout)
        self.assertIn("ask", res.stdout)

    def test_cli_parse_and_inspect(self):
        # 1. 创建临时 Markdown 文档
        test_file = WORKSPACE_ROOT / "test_cli_doc.md"
        test_file.write_text("# Chapter 1\nAI Reader parses markdown into AST seamlessly.\n# Chapter 2\nKnowledge graph and mindmaps.", encoding="utf-8")
        try:
            # 2. 执行解析
            res_parse = self.run_cli(["parse", str(test_file)])
            self.assertEqual(res_parse.returncode, 0)
            self.assertIn("[SUCCESS] Document parsed successfully", res_parse.stdout)

            # 3. 检查书籍列表
            res_books = self.run_cli(["books"])
            self.assertEqual(res_books.returncode, 0)
            self.assertIn("test_cli_doc", res_books.stdout)

            # 4. 执行 low-level invoke
            res_inv = self.run_cli(["invoke", "--action", "doc.list", "--pretty"])
            self.assertEqual(res_inv.returncode, 0)
            data = json.loads(res_inv.stdout)
            self.assertEqual(data.get("code"), 0)
            self.assertIn("books", data.get("data", {}))
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_cli_keywords_and_mindmap(self):
        res_kw = self.run_cli(["keywords", "1", "--top-k", "5"])
        self.assertEqual(res_kw.returncode, 0)
        self.assertIn("Keywords for Book #1", res_kw.stdout)

        res_mm = self.run_cli(["mindmap", "1"])
        self.assertEqual(res_mm.returncode, 0)
        self.assertIn("Mindmap Generated for Book #1", res_mm.stdout)

    def test_cli_ask_cognitive_companion(self):
        res_ask = self.run_cli(["ask", "1", "--template", "critical", "--text", "Cognitive limits"])
        self.assertEqual(res_ask.returncode, 0)
        self.assertIn("AI Cognitive Companion [critical]", res_ask.stdout)


if __name__ == "__main__":
    unittest.main()
