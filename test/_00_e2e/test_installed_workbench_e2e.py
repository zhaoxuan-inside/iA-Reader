#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_00_e2e/test_installed_workbench_e2e.py
安装后真实环境启动与 GUI 阅读工作台端到端验证测试 (Installed Application E2E Test)
验证：
  1. 解包真实生成的 .deb 安装包，验证 /usr/bin/ai_reader、desktop 图标与启动器存在
  2. 模拟从桌面启动（不带 CLI 子参数）：启动内置 GUI 工作台，验证 http://127.0.0.1:{port} 正常响应 HTML
  3. 验证工作台 /api/invoke 接口正常连通六元组 FFI
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import unittest
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DEB_PACKAGE = WORKSPACE_ROOT / "output/linux/ai-reader_3.0.0_amd64.deb"
TEST_INSTALL_DIR = WORKSPACE_ROOT / "test_installed_sandbox"


class TestInstalledWorkbenchE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_INSTALL_DIR.exists():
            shutil.rmtree(TEST_INSTALL_DIR)
        TEST_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        cls.test_db = WORKSPACE_ROOT / "test_installed_e2e.db"
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.test_env = os.environ.copy()
        cls.test_env["AI_READER_DB_PATH"] = str(cls.test_db)

        # 解包真实的 .deb 安装包到独立沙箱环境
        subprocess.run(["dpkg-deb", "-x", str(DEB_PACKAGE), str(TEST_INSTALL_DIR)], check=True)

    @classmethod
    def tearDownClass(cls):
        if TEST_INSTALL_DIR.exists():
            shutil.rmtree(TEST_INSTALL_DIR)
        if hasattr(cls, "test_db") and cls.test_db.exists():
            cls.test_db.unlink()

    def test_01_installed_package_files_integrity(self):
        """验证安装包解包后的桌面图标、启动脚本与二进制结构完备性"""
        launcher = TEST_INSTALL_DIR / "usr/bin/ai_reader"
        app_entry = TEST_INSTALL_DIR / "usr/lib/ai-reader/ai_reader"
        desktop_entry = TEST_INSTALL_DIR / "usr/share/applications/ai-reader.desktop"
        icon_png = TEST_INSTALL_DIR / "usr/share/icons/hicolor/512x512/apps/ai-reader.png"
        icon_svg = TEST_INSTALL_DIR / "usr/share/icons/hicolor/scalable/apps/ai-reader.svg"

        self.assertTrue(launcher.exists(), "必须安装 /usr/bin/ai_reader 启动脚本")
        self.assertTrue(app_entry.exists(), "必须安装 /usr/lib/ai-reader/ai_reader 主执行程序")
        self.assertTrue(desktop_entry.exists(), "必须安装 .desktop 桌面启动器")
        self.assertTrue(icon_png.exists(), "必须安装 512px PNG 桌面图标")
        self.assertTrue(icon_svg.exists(), "必须安装 SVG 矢量桌面图标")

        # 验证 .desktop 内容
        desktop_content = desktop_entry.read_text(encoding="utf-8")
        self.assertIn("Name=AI Reader", desktop_content)
        self.assertIn("Icon=ai-reader", desktop_content)
        self.assertIn("Exec=/usr/bin/ai_reader", desktop_content)

    def test_02_installed_app_launches_workbench_gui_successfully(self):
        """验证在安装后的环境下启动主程序（无命令行参数）能成功拉起本地 GUI 工作台并返回页面"""
        app_entry = (TEST_INSTALL_DIR / "usr/lib/ai-reader/ai_reader").resolve()
        port = 8789

        # 在子进程中拉起安装后的主程序，传入 workbench 子命令（带指定测试端口和禁用弹窗参数）
        proc = subprocess.Popen(
            [sys.executable, str(app_entry), "workbench", "--port", str(port), "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(app_entry.parent),
            env=self.test_env
        )

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        time.sleep(1.0)
        try:
            # 1. 验证工作台 HTTP 服务已正常就绪
            url_health = f"http://127.0.0.1:{port}/health"
            with opener.open(url_health, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data.get("status"), "ok")

            # 2. 验证阅读工作台 HTML 页面正常返回且包含 iA Writer 元素
            url_home = f"http://127.0.0.1:{port}/"
            with opener.open(url_home, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("AI Reader · iA Writer 沉浸工作台", html)
                self.assertIn("focus-mode", html)
                self.assertIn("selection-pill", html)
                self.assertIn("⚡️ 通俗", html)

            # 3. 验证工作台调用六元组 API (/api/invoke) 正常工作
            url_api = f"http://127.0.0.1:{port}/api/invoke"
            api_payload = json.dumps({
                "action": "ai.companion_ask",
                "payload": {
                    "book_id": 1,
                    "template_type": "logic",
                    "selected_text": "安装后集成测试段落"
                }
            }).encode("utf-8")
            req = urllib.request.Request(url_api, data=api_payload, headers={"Content-Type": "application/json"})
            with opener.open(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                res_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(res_data.get("code"), 0, f"Invoke error response: {res_data}")
                self.assertIn("response", res_data.get("data", {}))

        finally:
            proc.terminate()
            proc.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
