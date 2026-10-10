#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_01_method_test/test_frontend_specs.py
单元测试：验证 Flutter 客户端代码结构、Linux 原生 Runner、DESIGN.md 规范一致性、Focus Mode 状态机、
双 Tab 目录与知识导图、全量产品设计落地与 FFI 信封协议
"""

import os
import re
import json
import ctypes
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


class TestFrontendSpecificationsAndState(unittest.TestCase):
    def setUp(self):
        self.frontend_dir = WORKSPACE_ROOT / "frontend"
        self.design_file = WORKSPACE_ROOT / "DESIGN.md"

    def test_01_design_md_tokens_exist(self):
        """验证 DESIGN.md 中 iA Writer 核心 Token 的完整性"""
        self.assertTrue(self.design_file.exists(), "DESIGN.md 必须存在于项目根目录")
        content = self.design_file.read_text(encoding="utf-8")

        # 验证核心参照物与哲学
        self.assertIn("iA Writer", content)
        self.assertIn("Typography-first", content)

        # 验证核心色彩与透明度 Token
        self.assertIn("#007AFF", content, "必须定义亮色 iA 标志性光标蓝")
        self.assertIn("#38BDF8", content, "必须定义暗色天青蓝")
        self.assertIn("65%", content, "必须定义段落级弱化 65% 透明度")
        self.assertIn("680px ~ 720px", content, "必须定义黄金版心定宽区间")

    def test_02_flutter_codebase_structure(self):
        """验证 Flutter 项目结构与关键源文件齐套"""
        required_files = [
            "pubspec.yaml",
            "lib/main.dart",
            "lib/core/theme/reader_theme.dart",
            "lib/core/ffi/reader_engine_bridge.dart",
            "lib/features/reader/presentation/controllers/focus_mode_controller.dart",
            "lib/features/selection_pill/presentation/floating_action_pill.dart",
            "lib/features/companion/presentation/companion_drawer.dart",
            "lib/features/mobile_sheet/presentation/mobile_companion_sheet.dart",
            "lib/features/toc_mindmap/presentation/toc_mindmap_drawer.dart",
        ]
        for rel_path in required_files:
            target = self.frontend_dir / rel_path
            self.assertTrue(target.exists(), f"关键文件缺少: {rel_path}")

    def test_03_reader_theme_tokens_match_design_md(self):
        """验证 reader_theme.dart 中的 Token 与 DESIGN.md 严格一致"""
        theme_path = self.frontend_dir / "lib/core/theme/reader_theme.dart"
        theme_code = theme_path.read_text(encoding="utf-8")

        self.assertIn("0xFF007AFF", theme_code, "代码中必须落地 lightAccentFocus: 0xFF007AFF")
        self.assertIn("0xFF38BDF8", theme_code, "代码中必须落地 darkAccentFocus: 0xFF38BDF8")
        self.assertIn("700.0", theme_code, "代码中必须落地 700px 黄金版心定宽")
        self.assertIn("0.65", theme_code, "代码中必须落地 0.65 柔和失焦弱化透明度")

    def test_04_focus_mode_controller_logic(self):
        """验证 focus_mode_controller.dart 中的状态机逻辑与方法完备度"""
        ctrl_path = self.frontend_dir / "lib/features/reader/presentation/controllers/focus_mode_controller.dart"
        ctrl_code = ctrl_path.read_text(encoding="utf-8")

        self.assertIn("getParagraphOpacity", ctrl_code, "必须包含透明度计算方法")
        self.assertIn("focusParagraph", ctrl_code, "必须包含段落聚焦触发")
        self.assertIn("exitFocusMode", ctrl_code, "必须包含 Esc / 恢复全明方法")
        self.assertIn("toggleFocusMode", ctrl_code, "必须包含快捷键切换逻辑")

    def test_05_companion_drawer_and_pill_interactions(self):
        """验证伴读抽屉支持 4 大模板、原位追问与持久化边注保存"""
        drawer_path = self.frontend_dir / "lib/features/companion/presentation/companion_drawer.dart"
        drawer_code = drawer_path.read_text(encoding="utf-8")

        self.assertIn("onAskFollowUp", drawer_code, "伴读抽屉必须支持卡片内原位追问")
        self.assertIn("onSaveAnnotation", drawer_code, "伴读抽屉必须支持保存段落边注")
        self.assertIn("追问本段细节", drawer_code, "必须具备极简输入框提示文案")

        pill_path = self.frontend_dir / "lib/features/selection_pill/presentation/floating_action_pill.dart"
        pill_code = pill_path.read_text(encoding="utf-8")
        self.assertIn("⚡️ 通俗", pill_code)
        self.assertIn("🔗 逻辑", pill_code)
        self.assertIn("🧐 批判", pill_code)
        self.assertIn("📖 术语", pill_code)
        self.assertIn("🖍 高亮", pill_code)

    def test_06_ffi_bridge_six_tuple_envelope_compliance(self):
        """验证 FFI 桥接客户端与六元组信封结构的兼容性"""
        bridge_path = self.frontend_dir / "lib/core/ffi/reader_engine_bridge.dart"
        bridge_code = bridge_path.read_text(encoding="utf-8")

        self.assertIn("class InvokeEnvelope", bridge_code, "必须定义统一六元组信封类")
        self.assertIn("ai.companion_ask", bridge_code, "必须支持伴读调用 action")
        self.assertIn("annotation.save", bridge_code, "必须支持批注持久化 action")
        self.assertIn("doc.get", bridge_code, "必须支持获取文档章节与段落 action")
        self.assertIn("mindmap.generate", bridge_code, "必须支持导图生成 action")

    def test_07_flutter_linux_runner_structure(self):
        """验证 Flutter Linux 原生 Runner 项目结构完整配置"""
        linux_runner_files = [
            "linux/CMakeLists.txt",
            "linux/main.cc",
            "linux/my_application.h",
            "linux/my_application.cc",
            "linux/flutter/CMakeLists.txt",
            "linux/flutter/generated_plugin_registrant.h",
            "linux/flutter/generated_plugin_registrant.cc",
        ]
        for rel_path in linux_runner_files:
            target = self.frontend_dir / rel_path
            self.assertTrue(target.exists(), f"Flutter Linux runner 缺少必要文件: {rel_path}")

    def test_08_toc_and_mindmap_drawer_specs(self):
        """验证 TocMindmapDrawer 具备章节 AST 与全书知识导图/词云双 Tab 支持"""
        drawer_path = self.frontend_dir / "lib/features/toc_mindmap/presentation/toc_mindmap_drawer.dart"
        code = drawer_path.read_text(encoding="utf-8")

        self.assertIn("章节 AST 目录", code, "必须具备章节 AST 目录树 Tab")
        self.assertIn("知识导图 & 词云", code, "必须具备全书知识导图与词云 Tab")
        self.assertIn("260.0", code, "抽屉宽度必须遵循 260px 规范")
        self.assertIn("onSectionSelected", code, "必须支持点击章节跳转")
        self.assertIn("onKeywordSelected", code, "必须支持点击核心关键词")

    def test_09_full_product_design_integration_in_main(self):
        """验证 main.dart 全面完成 PRD 与 DESIGN.md 的全部产品设计要求"""
        main_path = self.frontend_dir / "lib/main.dart"
        code = main_path.read_text(encoding="utf-8")

        # 1. 顶栏 44px 自动淡出隐退
        self.assertIn("_isHeaderVisible", code)
        self.assertIn("chromeFadeDuration", code)

        # 2. 700px 黄金版心与 Focus Mode
        self.assertIn("readingGoldenWidth", code)
        self.assertIn("focusTransitionDuration", code)

        # 3. 划词悬浮胶囊 5 按钮与高亮
        self.assertIn("FloatingActionPill", code)
        self.assertIn("_handleHighlight", code)

        # 4. 伴读抽屉原位追问与边注保存
        self.assertIn("CompanionDrawer", code)
        self.assertIn("_paragraphAnnotations", code)

        # 5. 键盘全导航
        self.assertIn("LogicalKeyboardKey.keyD", code)
        self.assertIn("LogicalKeyboardKey.escape", code)
        self.assertIn("LogicalKeyboardKey.backslash", code)
        self.assertIn("LogicalKeyboardKey.keyJ", code)
        self.assertIn("LogicalKeyboardKey.keyK", code)

        # 6. 移动端自适应 Bottom Sheet
        self.assertIn("MobileCompanionSheet", code)

    def test_10_c_abi_native_shared_library(self):
        """验证编译产出的真实 libreader_core.so 能够被原生 C-ABI 加载并执行"""
        so_path = WORKSPACE_ROOT / "backend/target/release/libreader_core.so"
        self.assertTrue(so_path.exists(), "必须存在编译好的 libreader_core.so 动态链接库")

        lib = ctypes.CDLL(str(so_path))
        lib.ai_reader_invoke.restype = ctypes.c_char_p
        lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.ai_reader_free_string.argtypes = [ctypes.c_char_p]

        res_bytes = lib.ai_reader_invoke(b"doc.list", b"{}")
        self.assertIsNotNone(res_bytes)
        res_str = res_bytes.decode("utf-8")
        data = json.loads(res_str)
        self.assertEqual(data.get("code"), 0, "C-ABI 动态库调用 doc.list 必须返回 code 0")
        self.assertIn("books", data.get("data", {}))


if __name__ == "__main__":
    unittest.main()
