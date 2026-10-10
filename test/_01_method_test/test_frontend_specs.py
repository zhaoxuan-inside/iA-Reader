#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_01_method_test/test_frontend_specs.py
单元测试：验证 Flutter 客户端代码结构、DESIGN.md 规范一致性、Focus Mode 状态机与 FFI 信封协议
"""

import os
import re
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


if __name__ == "__main__":
    unittest.main()
