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
DEB_PACKAGE = WORKSPACE_ROOT / "output/linux/ai-reader_0.0.1_amd64.deb"
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

    def test_02_installed_app_is_pure_inprocess_native_client(self):
        """验证安装后的 GUI 工作台为纯进程内原生 IPC 架构，已彻底废除本地 HTTP Server / 端口监听"""
        workbench_file = TEST_INSTALL_DIR / "usr/lib/ai-reader/gui_workbench.py"
        self.assertTrue(workbench_file.exists(), "必须安装 gui_workbench.py 原生客户端视窗模块")

        content = workbench_file.read_text(encoding="utf-8")

        # 1. 验证已彻底移除 HTTP Server 与 fetch 接口
        self.assertNotIn("class WorkbenchHTTPHandler", content, "必须彻底移除本地 HTTP 服务类")
        self.assertNotIn('fetch("/api/invoke"', content, "必须彻底移除前端 fetch HTTP 调用")
        self.assertNotIn("http.server", content, "必须彻底剔除 http.server 依赖")

        # 2. 验证已全面接入进程内 Native IPC 消息通道
        self.assertIn("window.webkit.messageHandlers.nativeEngine", content, "必须接入 WebKit2 原生脚本消息管道")
        self.assertIn("register_script_message_handler", content, "必须注册原生 nativeEngine 处理程序")
        self.assertIn("load_html", content, "必须使用本地 load_html 加载页面，不走网络端口")

        # 3. 验证通过子进程调用安装态主程序无头 workbench 正常执行
        app_entry = (TEST_INSTALL_DIR / "usr/lib/ai-reader/ai_reader").resolve()
        res_wb = subprocess.run(
            [sys.executable, str(app_entry), "workbench", "--no-gui"],
            capture_output=True,
            text=True,
            cwd=str(app_entry.parent),
            env=self.test_env,
            timeout=5
        )
        self.assertEqual(res_wb.returncode, 0)
        self.assertIn("Headless mode", res_wb.stdout)

        # 4. 验证安装态程序六元组 invoke 原生直接调用工作正常
        invoke_payload = json.dumps({
            "book_id": 1,
            "template_type": "logic",
            "selected_text": "安装态零HTTP原生调用验证段落"
        })
        res_inv = subprocess.run(
            [sys.executable, str(app_entry), "invoke", "--action", "ai.companion_ask", "--payload", invoke_payload],
            capture_output=True,
            text=True,
            cwd=str(app_entry.parent),
            env=self.test_env,
            timeout=5
        )
        json_lines = [l.strip() for l in res_inv.stdout.strip().split("\n") if l.strip().startswith("{")]
        self.assertTrue(bool(json_lines), f"No JSON output found in stdout: {res_inv.stdout}")
        res_json = json.loads(json_lines[-1])
        self.assertEqual(res_json.get("code"), 0)
        self.assertIn("response", res_json.get("data", {}))


if __name__ == "__main__":
    unittest.main()
