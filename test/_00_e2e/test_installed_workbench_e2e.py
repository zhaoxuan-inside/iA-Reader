#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_00_e2e/test_installed_workbench_e2e.py
安装后真实环境启动与端到端验证测试 (Installed Application E2E Test)
验证：
  1. 系统全局真实已安装的 ai-reader 软件包 (dpkg -l)、/usr/bin/ai_reader、desktop 图标与启动器
  2. 直接调用系统已安装的 /usr/bin/ai_reader 命令行与六元组 invoke 原生直接调用
  3. 验证桌面启动器与零端口原生架构
"""

import os
import sys
import json
import shutil
import unittest
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DEB_PACKAGE = WORKSPACE_ROOT / "output/linux/ai-reader_0.0.1_amd64.deb"


class TestInstalledWorkbenchE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = WORKSPACE_ROOT / "test_installed_e2e.db"
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.test_env = os.environ.copy()
        cls.test_env["AI_READER_DB_PATH"] = str(cls.test_db)

        # 确保通过 dpkg -i 真实安装至系统
        if DEB_PACKAGE.exists():
            subprocess.run(["sudo", "dpkg", "-i", str(DEB_PACKAGE)], check=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db") and cls.test_db.exists():
            cls.test_db.unlink()

    def test_01_system_dpkg_package_installed(self):
        """验证操作系统 dpkg 数据库中已真实安装 ai-reader 软件包"""
        res = subprocess.run(["dpkg", "-l", "ai-reader"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, "dpkg -l 必须能查询到已安装的 ai-reader 包")
        self.assertIn("ai-reader", res.stdout)
        self.assertIn("0.0.1", res.stdout)

    def test_02_system_installed_files_integrity(self):
        """验证系统全局路径中已安装的可执行程序、桌面图标与启动脚本"""
        launcher = Path("/usr/bin/ai_reader")
        app_entry = Path("/usr/lib/ai-reader/ai_reader")
        desktop_entry = Path("/usr/share/applications/ai-reader.desktop")
        icon_png = Path("/usr/share/icons/hicolor/512x512/apps/ai-reader.png")
        icon_svg = Path("/usr/share/icons/hicolor/scalable/apps/ai-reader.svg")

        self.assertTrue(launcher.exists(), "必须安装 /usr/bin/ai_reader 系统可执行文件")
        self.assertTrue(app_entry.exists(), "必须安装 /usr/lib/ai-reader/ai_reader 主执行程序")
        self.assertTrue(desktop_entry.exists(), "必须安装 /usr/share/applications/ai-reader.desktop 桌面启动器")
        self.assertTrue(icon_png.exists(), "必须安装 512px PNG 桌面图标")
        self.assertTrue(icon_svg.exists(), "必须安装 SVG 矢量桌面图标")

        # 验证 .desktop 内容
        desktop_content = desktop_entry.read_text(encoding="utf-8")
        self.assertIn("Name=AI Reader", desktop_content)
        self.assertIn("Icon=ai-reader", desktop_content)
        self.assertIn("Exec=/usr/bin/ai_reader", desktop_content)

    def test_03_system_binary_execution_e2e(self):
        """直接从操作系统 PATH 调用已安装的 /usr/bin/ai_reader 进行端到端验证"""
        # 1. 验证帮助命令
        res_help = subprocess.run(["/usr/bin/ai_reader", "--help"], capture_output=True, text=True, timeout=5)
        self.assertEqual(res_help.returncode, 0)
        self.assertIn("AI Reader", res_help.stdout)

        # 2. 验证六元组 invoke 原生直接调用
        invoke_payload = json.dumps({
            "book_id": 1,
            "template_type": "logic",
            "selected_text": "真实系统安装态端到端测试段落"
        })
        res_inv = subprocess.run(
            ["/usr/bin/ai_reader", "invoke", "--action", "ai.companion_ask", "--payload", invoke_payload],
            capture_output=True,
            text=True,
            env=self.test_env,
            timeout=5
        )
        self.assertEqual(res_inv.returncode, 0)
        json_lines = [l.strip() for l in res_inv.stdout.strip().split("\n") if l.strip().startswith("{")]
        self.assertTrue(bool(json_lines), f"No JSON output found in stdout: {res_inv.stdout}")
        res_json = json.loads(json_lines[-1])
        self.assertEqual(res_json.get("code"), 0)
        self.assertIn("response", res_json.get("data", {}))


if __name__ == "__main__":
    unittest.main()
