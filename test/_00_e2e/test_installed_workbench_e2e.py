#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_00_e2e/test_installed_workbench_e2e.py
安装态端到端验证测试 (Installed Application E2E Test)

双模式：
  - 装机模式（默认）：验证真实 dpkg 安装的系统路径 /usr/bin/ai_reader 等
    （需要 sudo dpkg -i，由 setUpClass 自动执行）
  - 抽取模式：AI_READER_DEB_ROOT=<dir> 时，将 deb 解包到该目录后对同构布局
    做等价验证——无 root 环境（容器/CI）的装机态替代路径，布局断言完全一致
验证：
  1. 包内完整布局：入口 shim / GUI bundle / 无头 CLI / Rust 引擎 / desktop / 图标
  2. 入口可执行 + 六元组 invoke 直调（CLI 与 GUI 同引擎）
  3. Python 引擎残留 = 失败（统一 Rust 引擎契约）
"""

import os
import sys
import json
import shutil
import unittest
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = WORKSPACE_ROOT / "VERSION"
CURRENT_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.1"
DEB_PACKAGE = WORKSPACE_ROOT / f"output/linux/ai-reader_{CURRENT_VERSION}_amd64.deb"


class TestInstalledWorkbenchE2E(unittest.TestCase):
    # 抽取模式根目录（AI_READER_DEB_ROOT 设置时启用）；装机模式为 None
    extracted_root = None

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.test_db = Path(tempfile.mkdtemp(prefix="ai_reader_installed_")) / "test_installed_e2e.db"
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.test_env = os.environ.copy()
        cls.test_env["AI_READER_HOME"] = str(tempfile.mkdtemp(prefix="ai_reader_installed_home_"))

        deb_root_env = os.environ.get("AI_READER_DEB_ROOT")
        if deb_root_env:
            # 抽取模式：dpkg-deb -x 解包到指定目录，无 root 完成布局级验证
            cls.extracted_root = Path(deb_root_env)
            cls.extracted_root.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["dpkg-deb", "-x", str(DEB_PACKAGE), str(cls.extracted_root)],
                check=True,
            )
        else:
            # 装机模式：确保通过 dpkg -i 真实安装至系统
            if DEB_PACKAGE.exists():
                subprocess.run(["sudo", "dpkg", "-i", str(DEB_PACKAGE)], check=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db") and cls.test_db.exists():
            cls.test_db.unlink()

    @classmethod
    def sys_path(cls, rel: str) -> Path:
        """系统路径解析：装机模式 → 真实根；抽取模式 → 解包根"""
        if cls.extracted_root is not None:
            return cls.extracted_root / rel.lstrip("/")
        return Path(rel)

    def entry_bin(self) -> list:
        """入口可执行：装机模式走 /usr/bin/ai_reader；抽取模式 shim 的绝对路径
        指向真实 /usr，需直接调用包内 CLI 等价物"""
        if self.extracted_root is not None:
            return [str(self.sys_path("/usr/lib/ai-reader/bin/ai-reader-cli"))]
        return ["/usr/bin/ai_reader"]

    def test_01_system_dpkg_package_installed(self):
        """验证操作系统 dpkg 数据库中已真实安装 ai-reader 软件包"""
        if self.extracted_root is not None:
            # 抽取模式：以 deb 包身份代替 dpkg 数据库断言
            import re
            res = subprocess.run(
                ["dpkg-deb", "-f", str(DEB_PACKAGE), "Package"], capture_output=True, text=True
            )
            self.assertEqual(res.stdout.strip(), "ai-reader")
            ver = subprocess.run(
                ["dpkg-deb", "-f", str(DEB_PACKAGE), "Version"], capture_output=True, text=True
            )
            self.assertEqual(ver.stdout.strip(), CURRENT_VERSION, "deb 版本必须与 VERSION 一致")
            return
        res = subprocess.run(["dpkg", "-l", "ai-reader"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, "dpkg -l 必须能查询到已安装的 ai-reader 包")
        self.assertIn("ai-reader", res.stdout)
        self.assertIn(CURRENT_VERSION, res.stdout)

    def test_02_system_installed_files_integrity(self):
        """验证系统全局路径中已安装的可执行程序、桌面图标与启动脚本（launcher 架构布局）"""
        entry = Path("/usr/bin/ai_reader")                            # 稳定入口 shim
        app_entry = Path("/usr/lib/ai-reader/bundle/ai_reader")       # Flutter 主执行程序
        cli_bin = Path("/usr/lib/ai-reader/bin/ai-reader-cli")        # 无头 CLI（Rust，与 GUI 同引擎）
        engine_lib = Path("/usr/lib/ai-reader/lib/libreader_core.so")  # Rust 引擎（唯一事实源）
        desktop_entry = Path("/usr/share/applications/ai-reader.desktop")
        icon_png = Path("/usr/share/icons/hicolor/512x512/apps/ai-reader.png")
        icon_svg = Path("/usr/share/icons/hicolor/scalable/apps/ai-reader.svg")

        entry = self.sys_path("/usr/bin/ai_reader")
        app_entry = self.sys_path("/usr/lib/ai-reader/bundle/ai_reader")
        cli_bin = self.sys_path("/usr/lib/ai-reader/bin/ai-reader-cli")
        engine_lib = self.sys_path("/usr/lib/ai-reader/lib/libreader_core.so")
        desktop_entry = self.sys_path("/usr/share/applications/ai-reader.desktop")
        icon_png = self.sys_path("/usr/share/icons/hicolor/512x512/apps/ai-reader.png")
        icon_svg = self.sys_path("/usr/share/icons/hicolor/scalable/apps/ai-reader.svg")

        self.assertTrue(entry.exists(), "必须安装 /usr/bin/ai_reader 系统入口")
        self.assertTrue(app_entry.exists(), "必须安装 /usr/lib/ai-reader/bundle/ai_reader Flutter 主执行程序")
        self.assertTrue(cli_bin.exists(), "必须安装无头 CLI /usr/lib/ai-reader/bin/ai-reader-cli")
        self.assertTrue(engine_lib.exists(), "必须安装 Rust 引擎动态库 libreader_core.so")
        self.assertFalse(
            self.sys_path("/usr/lib/ai-reader/ai_reader_app.py").exists(),
            "Python 引擎已移除：不得残留旧启动器",
        )
        self.assertFalse(
            self.sys_path("/usr/lib/ai-reader/backend").exists(),
            "Python 引擎已移除：不得残留 backend 目录",
        )
        self.assertTrue(desktop_entry.exists(), "必须安装 /usr/share/applications/ai-reader.desktop 桌面启动器")
        self.assertTrue(icon_png.exists(), "必须安装 512px PNG 桌面图标")
        self.assertTrue(icon_svg.exists(), "必须安装 SVG 矢量桌面图标")

        # 入口 shim：无参 → GUI bundle；带参 → 无头 CLI
        shim_content = entry.read_text(encoding="utf-8")
        self.assertIn("/usr/lib/ai-reader/bundle/ai_reader", shim_content, "无参应启动 GUI bundle")
        self.assertIn("/usr/lib/ai-reader/bin/ai-reader-cli", shim_content, "带参应转发无头 CLI")

        # 验证 .desktop 内容
        desktop_content = desktop_entry.read_text(encoding="utf-8")
        self.assertIn("Name=AI Reader", desktop_content)
        self.assertIn("Icon=ai-reader", desktop_content)
        self.assertIn("Exec=/usr/bin/ai_reader", desktop_content)

    def test_03_system_binary_execution_e2e(self):
        """直接从操作系统 PATH 调用已安装的 /usr/bin/ai_reader 进行端到端验证"""
        # 1. 验证帮助命令
        res_help = subprocess.run(self.entry_bin() + ["--help"], capture_output=True, text=True, timeout=5)
        self.assertEqual(res_help.returncode, 0)
        self.assertIn("AI Reader", res_help.stdout)

        # 2. 验证六元组 invoke 原生直接调用
        invoke_payload = json.dumps({
            "book_id": 1,
            "template_type": "logic",
            "selected_text": "真实系统安装态端到端测试段落"
        })
        res_inv = subprocess.run(
            self.entry_bin() + ["invoke", "--action", "ai.companion_ask", "--payload", invoke_payload],
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
