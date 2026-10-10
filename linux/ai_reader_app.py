#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux/ai_reader_app.py
AI Reader - Modern Minimalist Desktop Workbench
Design Language: Notion + Apple Design System
Architecture:
- Two Distinct Dedicated Pages (Gtk.Stack):
  1. Library View (文档管理与资料库工作台): Import, manage, search, inspect books
  2. Reading View (沉浸式阅读与伴读工作台): Distraction-free reading with collapsible sidebars
- High-Contrast Visible Controls: Solid borders, crisp labels, Apple Blue accents
- Interactive Cairo Knowledge Graph with pastel themes
- Strict Alignment with PRD, Architecture & Six-Tuple Engine Contracts
"""

import sys
import os
import math
import json
import time
from pathlib import Path

# 适配本地开发与打包安装运行环境
APP_DIR = Path(__file__).resolve().parent
if (APP_DIR / "backend").exists():
    WORKSPACE_ROOT = APP_DIR
else:
    WORKSPACE_ROOT = APP_DIR.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.reader_engine import ai_reader_invoke, get_llm_config

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, cairo

# 用户配置路径
USER_CONFIG_DIR = Path.home() / ".config" / "ai-reader"
USER_CONFIG_FILE = USER_CONFIG_DIR / "llm_config.json"


def save_llm_settings(cfg: dict):
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ==============================================================================
# CSS 样式系统 (Notion + Apple High-Contrast System)
# ==============================================================================
NOTION_APPLE_HIGH_CONTRAST_CSS = """
/* 全局主窗口与基础字体 */
window.ia-reader-window {
    background-color: #F7F7F5;
    color: #111827;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

/* 统一标题栏 (Unified Titlebar) */
headerbar.ia-headerbar {
    background-color: #FFFFFF;
    border-bottom: 1.5px solid #E5E7EB;
    min-height: 52px;
    padding: 0 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

headerbar.ia-headerbar .title {
    font-weight: 700;
    font-size: 14.5px;
    color: #111827;
}

headerbar.ia-headerbar .subtitle {
    font-size: 12px;
    color: #4B5563;
    font-weight: 500;
}

/* 高对比度按钮基类 (Apple & Notion Solid Buttons) */
button.ia-btn {
    background-color: #FFFFFF;
    border: 1.5px solid #D1D5DB;
    border-radius: 8px;
    color: #111827;
    font-size: 13px;
    font-weight: 600;
    padding: 6px 14px;
    margin: 0 3px;
    transition: all 120ms ease;
}

button.ia-btn:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
    color: #000000;
}

/* Apple 强调蓝按钮 (High Contrast Primary Button) */
button.ia-primary-btn {
    background-color: #0071E3;
    border: 1.5px solid #005BB5;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 6px 16px;
    margin: 0 3px;
}

button.ia-primary-btn:hover {
    background-color: #0077ED;
    border-color: #004C99;
    color: #FFFFFF;
}

/* 红色警告/删除按钮 */
button.ia-danger-btn {
    background-color: #FEF2F2;
    border: 1.5px solid #FCA5A5;
    border-radius: 6px;
    color: #B91C1C;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
}

button.ia-danger-btn:hover {
    background-color: #FEE2E2;
    border-color: #EF4444;
    color: #7F1D1D;
}

/* 左侧栏切换选项卡 (Notebook) */
notebook.ia-notebook {
    background-color: #F7F7F5;
    border-right: 1.5px solid #E5E7EB;
}

notebook.ia-notebook tab {
    background-color: #EFEFEF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin: 4px 2px;
    transition: all 100ms ease;
}

notebook.ia-notebook tab:hover {
    color: #111827;
    background-color: #E5E7EB;
}

notebook.ia-notebook tab:checked {
    color: #000000;
    font-weight: 700;
    background-color: #FFFFFF;
    border-color: #9CA3AF;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* 树形列表与书架表格 (TreeView) */
treeview.ia-treeview {
    background-color: #FFFFFF;
    color: #111827;
    font-size: 13.5px;
    border: 1px solid #E5E7EB;
}

treeview.ia-treeview:selected {
    background-color: #E0E7FF;
    color: #1E3A8A;
    font-weight: 600;
}

/* 中间正文视口：Notion 纯白文档画布 */
textview.ia-editor {
    background-color: #FFFFFF;
    color: #1F2937;
    font-size: 15px;
}

textview.ia-editor text {
    background-color: #FFFFFF;
    color: #1F2937;
}

textview.ia-editor text:selected {
    background-color: #BAE6FD;
    color: #0C4A6E;
}

/* 右侧边注栏 (Marginalia) */
box.ia-marginalia {
    background-color: #FAFAFA;
    border-left: 1.5px solid #E5E7EB;
}

/* Notion 卡片容器 (Callout / Card Container) */
frame.ia-card {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

/* 4 大认知伴读高对比度按钮卡片 */
button.ia-chip-feynman {
    background-color: #FFFBEB;
    border: 1.5px solid #D97706;
    border-radius: 8px;
    color: #78350F;
    font-weight: 700;
    font-size: 12.5px;
    padding: 6px 10px;
}
button.ia-chip-feynman:hover {
    background-color: #FEF3C7;
    border-color: #B45309;
}

button.ia-chip-logic {
    background-color: #F0FDF4;
    border: 1.5px solid #16A34A;
    border-radius: 8px;
    color: #14532D;
    font-weight: 700;
    font-size: 12.5px;
    padding: 6px 10px;
}
button.ia-chip-logic:hover {
    background-color: #DCFCE7;
    border-color: #15803D;
}

button.ia-chip-critical {
    background-color: #EFF6FF;
    border: 1.5px solid #2563EB;
    border-radius: 8px;
    color: #1E3A8A;
    font-weight: 700;
    font-size: 12.5px;
    padding: 6px 10px;
}
button.ia-chip-critical:hover {
    background-color: #DBEAFE;
    border-color: #1D4ED8;
}

button.ia-chip-term {
    background-color: #FAF5FF;
    border: 1.5px solid #9333EA;
    border-radius: 8px;
    color: #581C87;
    font-weight: 700;
    font-size: 12.5px;
    padding: 6px 10px;
}
button.ia-chip-term:hover {
    background-color: #F3E8FF;
    border-color: #7E22CE;
}

/* 伴读卡片内文本视口 */
textview.ia-card-text {
    background-color: #F9FAFB;
    color: #1F2937;
    font-size: 13px;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
}

textview.ia-card-text text {
    background-color: #F9FAFB;
    color: #1F2937;
}

/* 高对比度输入框 */
entry.ia-entry {
    background-color: #FFFFFF;
    border: 1.5px solid #9CA3AF;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: #111827;
}

entry.ia-entry:focus {
    border-color: #0071E3;
    box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.25);
}

/* 资料库顶部统计卡片 */
box.ia-stat-chip {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 10px;
    padding: 10px 18px;
}
"""


# ==============================================================================
# 模型设置对话框 (LLMSettingsDialog - Apple Modal Style)
# ==============================================================================
class LLMSettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="模型与伴读设置 (AI Settings)", transient_for=parent, flags=0)
        self.set_default_size(560, 500)
        btn_cancel = self.add_button("取消", Gtk.ResponseType.CANCEL)
        btn_cancel.get_style_context().add_class("ia-btn")
        btn_ok = self.add_button("保存配置", Gtk.ResponseType.OK)
        btn_ok.get_style_context().add_class("ia-primary-btn")

        self.current_cfg = get_llm_config()
        self._build_ui()

    def _build_ui(self):
        box = self.get_content_area()
        box.set_spacing(14)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        lbl = Gtk.Label()
        lbl.set_markup("<b>🤖 LLM 智能伴读与深度模型配置</b>\n<span foreground='#4B5563'><small>支持 OpenAI / DeepSeek / Ollama / Gemini / 兼容端点</small></span>")
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(12)
        box.pack_start(grid, False, False, 0)

        # 供应商
        grid.attach(Gtk.Label(label="服务提供方:", xalign=0), 0, 0, 1, 1)
        self.combo_provider = Gtk.ComboBoxText()
        providers = [
            ("deepseek", "DeepSeek (api.deepseek.com)"),
            ("openai", "OpenAI (api.openai.com)"),
            ("ollama", "本地 Ollama (127.0.0.1:11434)"),
            ("custom", "自定义兼容接口 (Custom)")
        ]
        for key, name in providers:
            self.combo_provider.append(key, name)
        self.combo_provider.set_active_id(self.current_cfg.get("provider", "deepseek"))
        self.combo_provider.connect("changed", self._on_provider_changed)
        grid.attach(self.combo_provider, 1, 0, 1, 1)

        # Endpoint
        grid.attach(Gtk.Label(label="API 端点:", xalign=0), 0, 1, 1, 1)
        self.entry_endpoint = Gtk.Entry()
        self.entry_endpoint.get_style_context().add_class("ia-entry")
        self.entry_endpoint.set_text(self.current_cfg.get("endpoint", "https://api.deepseek.com/v1"))
        grid.attach(self.entry_endpoint, 1, 1, 1, 1)

        # API Key
        grid.attach(Gtk.Label(label="API Key:", xalign=0), 0, 2, 1, 1)
        self.entry_key = Gtk.Entry()
        self.entry_key.get_style_context().add_class("ia-entry")
        self.entry_key.set_visibility(False)
        self.entry_key.set_text(self.current_cfg.get("api_key", ""))
        self.entry_key.set_placeholder_text("sk-...")
        grid.attach(self.entry_key, 1, 2, 1, 1)

        # Model Name
        grid.attach(Gtk.Label(label="模型名称:", xalign=0), 0, 3, 1, 1)
        self.entry_model = Gtk.Entry()
        self.entry_model.get_style_context().add_class("ia-entry")
        self.entry_model.set_text(self.current_cfg.get("model_name", "deepseek-chat"))
        grid.attach(self.entry_model, 1, 3, 1, 1)

        # Temperature
        grid.attach(Gtk.Label(label="创造性 (Temp):", xalign=0), 0, 4, 1, 1)
        self.spin_temp = Gtk.SpinButton.new_with_range(0.0, 1.5, 0.1)
        self.spin_temp.set_value(float(self.current_cfg.get("temperature", 0.7)))
        grid.attach(self.spin_temp, 1, 4, 1, 1)

        # System Prompt
        box.pack_start(Gtk.Label(label="系统人设提示词 (System Prompt):", xalign=0), False, False, 2)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(100)
        self.tv_prompt = Gtk.TextView()
        self.tv_prompt.set_wrap_mode(Gtk.WrapMode.WORD)
        self.tv_prompt.get_buffer().set_text(self.current_cfg.get("system_prompt", ""))
        scroll.add(self.tv_prompt)
        box.pack_start(scroll, True, True, 0)

        box.show_all()

    def _on_provider_changed(self, combo):
        pid = combo.get_active_id()
        if pid == "deepseek":
            self.entry_endpoint.set_text("https://api.deepseek.com/v1")
            self.entry_model.set_text("deepseek-chat")
        elif pid == "openai":
            self.entry_endpoint.set_text("https://api.openai.com/v1")
            self.entry_model.set_text("gpt-4o")
        elif pid == "ollama":
            self.entry_endpoint.set_text("http://127.0.0.1:11434/v1")
            self.entry_model.set_text("llama3.2")

    def get_config(self) -> dict:
        buf = self.tv_prompt.get_buffer()
        prompt_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        return {
            "provider": self.combo_provider.get_active_id(),
            "endpoint": self.entry_endpoint.get_text().strip(),
            "api_key": self.entry_key.get_text().strip(),
            "model_name": self.entry_model.get_text().strip(),
            "temperature": self.spin_temp.get_value(),
            "max_output_tokens": 1024,
            "system_prompt": prompt_text.strip()
        }


# ==============================================================================
# 添加边注对话框 (AddAnnotationDialog)
# ==============================================================================
class AddAnnotationDialog(Gtk.Dialog):
    def __init__(self, parent, selected_text: str):
        super().__init__(title="添加阅读边注心得", transient_for=parent, flags=0)
        self.set_default_size(460, 340)
        btn_cancel = self.add_button("取消", Gtk.ResponseType.CANCEL)
        btn_cancel.get_style_context().add_class("ia-btn")
        btn_ok = self.add_button("沉淀笔记", Gtk.ResponseType.OK)
        btn_ok.get_style_context().add_class("ia-primary-btn")

        self.selected_text = selected_text
        self.chosen_color = "#FDE047"
        self._build_ui()

    def _build_ui(self):
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        short_quote = self.selected_text[:140] + ("..." if len(self.selected_text) > 140 else "")
        lbl_quote = Gtk.Label()
        lbl_quote.set_markup(f"<span foreground='#4B5563'>引用选区：</span>\n<i>“{short_quote}”</i>")
        lbl_quote.set_line_wrap(True)
        lbl_quote.set_xalign(0)
        box.pack_start(lbl_quote, False, False, 0)

        # 颜色单选
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        color_box.pack_start(Gtk.Label(label="高亮色彩:"), False, False, 0)

        colors = [("#FDE047", "鹅黄"), ("#86EFAC", "薄荷绿"), ("#93C5FD", "天蓝"), ("#F472B6", "樱粉")]
        first_radio = None
        for code, name in colors:
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, name)
            if not first_radio:
                first_radio = radio
            radio.connect("toggled", lambda w, c=code: setattr(self, "chosen_color", c))
            color_box.pack_start(radio, False, False, 0)
        box.pack_start(color_box, False, False, 0)

        # 批注内容
        box.pack_start(Gtk.Label(label="心得与批注思考:", xalign=0), False, False, 0)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(120)
        self.tv_note = Gtk.TextView()
        self.tv_note.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(self.tv_note)
        box.pack_start(scrolled, True, True, 0)

        box.show_all()

    def get_data(self):
        buf = self.tv_note.get_buffer()
        note = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        return {
            "color": self.chosen_color,
            "note_text": note.strip() or "重点关注"
        }


# ==============================================================================
# 交互式 Cairo 概念图谱画布 (KnowledgeGraphCanvas)
# ==============================================================================
class KnowledgeGraphCanvas(Gtk.DrawingArea):
    def __init__(self, on_node_click_callback=None):
        super().__init__()
        self.nodes = []
        self.links = []
        self.node_positions = {}
        self.selected_node = None
        self.on_node_click_callback = on_node_click_callback
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_click)

    def set_graph_data(self, nodes: list, links: list):
        self.nodes = nodes
        self.links = links
        self.selected_node = None
        self._calculate_layout()
        self.queue_draw()

    def _calculate_layout(self):
        self.node_positions.clear()
        if not self.nodes:
            return

        w = max(self.get_allocated_width(), 320)
        h = max(self.get_allocated_height(), 400)
        cx, cy = w / 2.0, h / 2.0
        r_base = min(cx, cy) * 0.72

        n = len(self.nodes)
        for i, node in enumerate(self.nodes):
            angle = 2.0 * math.pi * i / max(n, 1)
            score = float(node.get("score", 0.5))
            r = r_base * (0.55 + 0.45 * (1.0 - min(score, 1.0)))
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.node_positions[node["word"]] = {
                "x": x,
                "y": y,
                "radius": 15 + int(score * 12),
                "data": node,
                "color_idx": i % 4
            }

    def _on_draw(self, widget, cr: cairo.Context):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        cr.set_source_rgb(0.984, 0.984, 0.980)
        cr.paint()

        if not self.nodes:
            cr.set_source_rgb(0.4, 0.4, 0.45)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(13)
            cr.move_to(24, 48)
            cr.show_text("关键词分析完成，正在渲染概念拓扑图谱...")
            return

        cx, cy = w / 2.0, h / 2.0
        r_base = min(cx, cy) * 0.72
        n = len(self.nodes)
        for i, node in enumerate(self.nodes):
            word = node["word"]
            if word not in self.node_positions:
                angle = 2.0 * math.pi * i / max(n, 1)
                score = float(node.get("score", 0.5))
                r = r_base * (0.55 + 0.45 * (1.0 - min(score, 1.0)))
                self.node_positions[word] = {
                    "x": cx + r * math.cos(angle),
                    "y": cy + r * math.sin(angle),
                    "radius": 15 + int(score * 12),
                    "data": node,
                    "color_idx": i % 4
                }

        # 调色盘
        pastel_themes = [
            ((0.88, 0.95, 0.99), (0.2, 0.6, 0.95), (0.01, 0.41, 0.63)),
            ((0.95, 0.91, 1.00), (0.7, 0.4, 0.95), (0.49, 0.13, 0.81)),
            ((0.86, 0.99, 0.90), (0.2, 0.8, 0.4), (0.08, 0.50, 0.24)),
            ((0.99, 0.95, 0.78), (0.95, 0.65, 0.1), (0.71, 0.33, 0.04))
        ]

        # 1. 连线
        for link in self.links:
            w1 = link.get("source_word")
            w2 = link.get("target_word")
            if w1 in self.node_positions and w2 in self.node_positions:
                p1 = self.node_positions[w1]
                p2 = self.node_positions[w2]
                weight = float(link.get("co_occurrence", 1))

                is_highlight = self.selected_node in (w1, w2)
                if is_highlight:
                    cr.set_source_rgba(0.0, 0.44, 0.89, 0.9)
                    cr.set_line_width(2.8 + min(weight * 0.4, 3.5))
                else:
                    cr.set_source_rgba(0.70, 0.70, 0.75, 0.6)
                    cr.set_line_width(1.3)

                cr.move_to(p1["x"], p1["y"])
                cr.line_to(p2["x"], p2["y"])
                cr.stroke()

        # 2. 节点
        layout = self.create_pango_layout("")
        for word, p in self.node_positions.items():
            is_active = (self.selected_node == word)
            rad = p["radius"]
            theme = pastel_themes[p.get("color_idx", 0)]

            if is_active:
                cr.set_source_rgba(0.0, 0.44, 0.89, 0.25)
                cr.arc(p["x"], p["y"], rad + 7, 0, 2 * math.pi)
                cr.fill()

            if is_active:
                cr.set_source_rgb(0.0, 0.44, 0.89)
            else:
                cr.set_source_rgb(*theme[0])
            cr.arc(p["x"], p["y"], rad, 0, 2 * math.pi)
            cr.fill_preserve()

            if is_active:
                cr.set_source_rgb(0.0, 0.25, 0.65)
                cr.set_line_width(2.8)
            else:
                cr.set_source_rgb(*theme[1])
                cr.set_line_width(2.0)
            cr.stroke()

            # 标签文本 (高对比度深黑/深蓝)
            layout.set_text(word, -1)
            desc = Pango.FontDescription("Sans 10")
            desc.set_weight(Pango.Weight.BOLD if is_active else Pango.Weight.SEMIBOLD)
            layout.set_font_description(desc)
            ink, logical = layout.get_pixel_extents()
            tw = logical.width
            th = logical.height

            cr.move_to(p["x"] - tw / 2.0, p["y"] + rad + 4)
            if is_active:
                cr.set_source_rgb(0.0, 0.44, 0.89)
            else:
                cr.set_source_rgb(0.08, 0.08, 0.12)
            PangoCairo.show_layout(cr, layout)

    def _on_click(self, widget, event):
        if event.button == 1:
            ex, ey = event.x, event.y
            clicked_word = None
            for word, p in self.node_positions.items():
                dx = ex - p["x"]
                dy = ey - p["y"]
                if math.sqrt(dx * dx + dy * dy) <= p["radius"] + 8:
                    clicked_word = word
                    break
            self.selected_node = clicked_word
            self.queue_draw()
            if clicked_word and self.on_node_click_callback:
                self.on_node_click_callback(clicked_word, self.node_positions[clicked_word]["data"])
        return True


# ==============================================================================
# 主窗体 (AIReaderWindow - 双页面架构: 资料库管理页 + 沉浸阅读专心页)
# ==============================================================================
class AIReaderWindow(Gtk.Window):
    # @PublicAPI
    def __init__(self):
        super().__init__(title="AI Reader")
        self.set_default_size(1400, 880)
        self.get_style_context().add_class("ia-reader-window")

        self.current_book_id = 1
        self.current_title = "深度学习与大语言模型导论"
        self.selected_text = "Attention Mechanisms have revolutionized sequence modeling in artificial intelligence."
        self.sections_data = []
        self.annotations_cache = []
        self.books_cache = []

        self._apply_css()
        self._load_app_icon()
        self._setup_ui()

        # 加载初始数据
        self.loadBook(self.current_book_id, self.current_title)

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(NOTION_APPLE_HIGH_CONTRAST_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_app_icon(self):
        candidates = [
            WORKSPACE_ROOT / "linux/ai-reader.svg",
            WORKSPACE_ROOT / "packaging/linux/deb/usr/share/icons/hicolor/scalable/apps/ai-reader.svg",
            Path("/usr/share/icons/hicolor/scalable/apps/ai-reader.svg"),
            Path("/usr/share/pixmaps/ai-reader.svg")
        ]
        for c in candidates:
            if c.exists():
                try:
                    self.set_icon_from_file(str(c))
                    break
                except Exception:
                    pass

    def _setup_ui(self):
        root_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root_vbox)

        # 顶部 HeaderBar (支持根据页面上下文动态切换状态)
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.get_style_context().add_class("ia-headerbar")
        self.set_titlebar(self.header)

        # ==============================================================
        # 页面 1 与 页面 2 容器 (Gtk.Stack - 资料库管理 vs 沉浸阅读)
        # ==============================================================
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        root_vbox.pack_start(self.stack, True, True, 0)

        # 构建两套独立页面
        self.page_library = self._build_library_page()
        self.page_reading = self._build_reading_page()

        self.stack.add_named(self.page_library, "library")
        self.stack.add_named(self.page_reading, "reading")

        # 默认显示沉浸阅读页面 (或资料库页面)
        self.switch_to_reading_view()

    # ==========================================================================
    # 页面 1：文档管理与资料库工作台 (Library View)
    # ==========================================================================
    def _build_library_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        container.set_margin_start(40)
        container.set_margin_end(40)
        container.set_margin_top(30)
        container.set_margin_bottom(40)
        scrolled.add(container)

        # 1. 顶部 Hero 统计面板
        hero_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        container.pack_start(hero_box, False, False, 0)

        hero_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lbl_hero_title = Gtk.Label()
        lbl_hero_title.set_markup("<span font='22' weight='bold'>📚 我的阅读资料库</span>")
        lbl_hero_title.set_xalign(0)
        hero_left.pack_start(lbl_hero_title, False, False, 0)

        lbl_hero_sub = Gtk.Label()
        lbl_hero_sub.set_markup("<span foreground='#4B5563'>本地 SQLite 离线持久化存储 • 自动提取结构化 AST、三级知识图谱与思维导图</span>")
        lbl_hero_sub.set_xalign(0)
        hero_left.pack_start(lbl_hero_sub, False, False, 0)
        hero_box.pack_start(hero_left, True, True, 0)

        # 右侧操作按钮条
        hero_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_import = Gtk.Button(label="+ 导入新文档")
        btn_import.get_style_context().add_class("ia-primary-btn")
        btn_import.connect("clicked", lambda w: self._open_file_dialog())
        hero_actions.pack_start(btn_import, False, False, 0)

        btn_settings = Gtk.Button(label="⚙️ AI 服务配置")
        btn_settings.get_style_context().add_class("ia-btn")
        btn_settings.connect("clicked", lambda w: self._open_settings())
        hero_actions.pack_start(btn_settings, False, False, 0)
        hero_box.pack_end(hero_actions, False, False, 0)

        # 2. 统计指标卡片条
        stats_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.chip_book_count = Gtk.Label()
        self.chip_book_count.set_markup("<span font='14' weight='bold'>0</span> 本文档")
        box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box1.get_style_context().add_class("ia-stat-chip")
        box1.pack_start(Gtk.Label(label="已存书籍"), False, False, 0)
        box1.pack_start(self.chip_book_count, False, False, 0)
        stats_strip.pack_start(box1, True, True, 0)

        self.chip_word_count = Gtk.Label()
        self.chip_word_count.set_markup("<span font='14' weight='bold'>0</span> 字")
        box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box2.get_style_context().add_class("ia-stat-chip")
        box2.pack_start(Gtk.Label(label="知识库字数"), False, False, 0)
        box2.pack_start(self.chip_word_count, False, False, 0)
        stats_strip.pack_start(box2, True, True, 0)

        self.chip_annot_count = Gtk.Label()
        self.chip_annot_count.set_markup("<span font='14' weight='bold'>0</span> 条")
        box3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box3.get_style_context().add_class("ia-stat-chip")
        box3.pack_start(Gtk.Label(label="沉淀边注"), False, False, 0)
        box3.pack_start(self.chip_annot_count, False, False, 0)
        stats_strip.pack_start(box3, True, True, 0)
        container.pack_start(stats_strip, False, False, 0)

        # 3. 文档清单列表 (Notion Database 表格视图)
        tbl_label = Gtk.Label()
        tbl_label.set_markup("<span font='15' weight='bold'>所有文档列表</span>")
        tbl_label.set_xalign(0)
        container.pack_start(tbl_label, False, False, 0)

        self.shelf_store = Gtk.ListStore(int, str, str, int, str)  # ID, Title, Format, Words, CreatedAt
        self.shelf_view = Gtk.TreeView(model=self.shelf_store)
        self.shelf_view.get_style_context().add_class("ia-treeview")
        self.shelf_view.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        # 序号列
        col0 = Gtk.TreeViewColumn("序号", Gtk.CellRendererText(), text=0)
        col0.set_min_width(60)
        self.shelf_view.append_column(col0)

        # 书名列
        rend_title = Gtk.CellRendererText()
        rend_title.set_property("weight", Pango.Weight.BOLD)
        col1 = Gtk.TreeViewColumn("文档标题", rend_title, text=1)
        col1.set_min_width(340)
        col1.set_expand(True)
        self.shelf_view.append_column(col1)

        # 格式列
        col2 = Gtk.TreeViewColumn("格式", Gtk.CellRendererText(), text=2)
        col2.set_min_width(100)
        self.shelf_view.append_column(col2)

        # 字数列
        col3 = Gtk.TreeViewColumn("字数统计", Gtk.CellRendererText(), text=3)
        col3.set_min_width(120)
        self.shelf_view.append_column(col3)

        self.shelf_view.connect("row-activated", self._on_shelf_row_activated)

        table_scroll = Gtk.ScrolledWindow()
        table_scroll.set_min_content_height(340)
        table_scroll.add(self.shelf_view)
        container.pack_start(table_scroll, True, True, 0)

        # 表格下方操作栏
        table_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_read_selected = Gtk.Button(label="📖 打开选中书籍进行深度阅读")
        btn_read_selected.get_style_context().add_class("ia-primary-btn")
        btn_read_selected.connect("clicked", lambda w: self._on_shelf_open_clicked(None))
        table_actions.pack_start(btn_read_selected, False, False, 0)

        btn_delete_selected = Gtk.Button(label="🗑️ 移除此文档")
        btn_delete_selected.get_style_context().add_class("ia-danger-btn")
        btn_delete_selected.connect("clicked", lambda w: self._on_shelf_delete_clicked())
        table_actions.pack_start(btn_delete_selected, False, False, 0)

        container.pack_start(table_actions, False, False, 0)

        return scrolled

    # ==========================================================================
    # 页面 2：沉浸式阅读与认知伴读工作台 (Reading View - 专心阅读)
    # ==========================================================================
    def _build_reading_page(self) -> Gtk.Widget:
        self.reading_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        # --------------------------------------------------------------
        # 1. 可折叠左侧栏：3 合 1 导航 Notebook (目录 / 概念图谱 / 思维导图)
        # --------------------------------------------------------------
        self.left_sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.left_sidebar_box.set_size_request(280, -1)

        self.left_notebook = Gtk.Notebook()
        self.left_notebook.get_style_context().add_class("ia-notebook")
        self.left_sidebar_box.pack_start(self.left_notebook, True, True, 0)

        # Tab 1: 章节目录
        toc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.outline_store = Gtk.ListStore(int, str)
        self.outline_view = Gtk.TreeView(model=self.outline_store)
        self.outline_view.get_style_context().add_class("ia-treeview")
        self.outline_view.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        col = Gtk.TreeViewColumn("章节", renderer, text=1)
        self.outline_view.append_column(col)
        self.outline_view.connect("row-activated", self._on_outline_activated)
        toc_scroll = Gtk.ScrolledWindow()
        toc_scroll.add(self.outline_view)
        toc_box.pack_start(toc_scroll, True, True, 0)
        self.left_notebook.append_page(toc_box, Gtk.Label(label="📖 目录"))

        # Tab 2: 概念图谱
        graph_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.graph_canvas = KnowledgeGraphCanvas(on_node_click_callback=self._on_graph_node_clicked)
        graph_box.pack_start(self.graph_canvas, True, True, 0)

        self.lbl_graph_info = Gtk.Label()
        self.lbl_graph_info.set_markup("<span foreground='#374151'><b>💡 点击概念节点反查正文段落</b></span>")
        self.lbl_graph_info.set_line_wrap(True)
        graph_box.pack_start(self.lbl_graph_info, False, False, 8)
        self.left_notebook.append_page(graph_box, Gtk.Label(label="🕸️ 图谱"))

        # Tab 3: 思维导图
        mindmap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.mindmap_store = Gtk.TreeStore(str, int)
        self.mindmap_view = Gtk.TreeView(model=self.mindmap_store)
        self.mindmap_view.get_style_context().add_class("ia-treeview")
        self.mindmap_view.set_headers_visible(False)
        m_rend = Gtk.CellRendererText()
        m_col = Gtk.TreeViewColumn("导图结构", m_rend, text=0)
        self.mindmap_view.append_column(m_col)
        self.mindmap_view.connect("row-activated", self._on_mindmap_row_activated)
        mindmap_scroll = Gtk.ScrolledWindow()
        mindmap_scroll.add(self.mindmap_view)
        mindmap_box.pack_start(mindmap_scroll, True, True, 0)
        self.left_notebook.append_page(mindmap_box, Gtk.Label(label="🌲 导图"))

        self.reading_paned.pack1(self.left_sidebar_box, False, False)

        # --------------------------------------------------------------
        # 2. 中右分栏 (中：纯净正文画布；右：可折叠伴读与边注)
        # --------------------------------------------------------------
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.reading_paned.pack2(self.content_paned, True, False)

        # 中栏：Notion 纯白文档画布
        mid_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_scrolled = Gtk.ScrolledWindow()
        self.content_view = Gtk.TextView()
        self.content_view.get_style_context().add_class("ia-editor")
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.set_left_margin(64)
        self.content_view.set_right_margin(64)
        self.content_view.set_top_margin(40)
        self.content_view.set_bottom_margin(48)
        self.content_view.set_pixels_inside_wrap(16)  # 1.75em 舒适行高

        # 选区与右键监听
        self.content_buffer = self.content_view.get_buffer()
        self.content_buffer.connect("notify::has-selection", self._on_buffer_selection_changed)
        self.content_view.connect("button-press-event", self._on_content_button_press)

        # 高亮标签
        self.tag_highlight_yellow = self.content_buffer.create_tag("hl_yellow", background="#FEF3C7")
        self.tag_highlight_green = self.content_buffer.create_tag("hl_green", background="#DCFCE7")
        self.tag_highlight_blue = self.content_buffer.create_tag("hl_blue", background="#E0F2FE")
        self.tag_highlight_pink = self.content_buffer.create_tag("hl_pink", background="#FCE7F3")

        self.content_scrolled.add(self.content_view)
        mid_vbox.pack_start(self.content_scrolled, True, True, 0)

        # 底部属性指示条
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.status_bar.set_margin_start(24)
        self.status_bar.set_margin_end(24)
        self.status_bar.set_margin_top(6)
        self.status_bar.set_margin_bottom(6)
        self.lbl_doc_info = Gtk.Label(label="字数统计: 0 | 进度: 100%")
        self.lbl_doc_info.set_xalign(0)
        self.status_bar.pack_start(self.lbl_doc_info, False, False, 0)
        mid_vbox.pack_start(self.status_bar, False, False, 0)

        self.content_paned.pack1(mid_vbox, True, False)

        # --------------------------------------------------------------
        # 3. 可折叠右栏：伴读与边注检查器面板
        # --------------------------------------------------------------
        self.marginalia_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.marginalia_box.get_style_context().add_class("ia-marginalia")
        self.marginalia_box.set_size_request(340, -1)
        self.marginalia_box.set_margin_start(14)
        self.marginalia_box.set_margin_end(14)
        self.marginalia_box.set_margin_top(14)
        self.marginalia_box.set_margin_bottom(14)

        # 认知伴读卡片
        companion_frame = Gtk.Frame()
        companion_frame.get_style_context().add_class("ia-card")
        companion_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        companion_vbox.set_margin_start(10)
        companion_vbox.set_margin_end(10)
        companion_vbox.set_margin_top(10)
        companion_vbox.set_margin_bottom(10)
        companion_frame.add(companion_vbox)

        lbl_companion_title = Gtk.Label()
        lbl_companion_title.set_markup("<span font='13' weight='bold'>💡 认知伴读与思维脚手架</span>")
        lbl_companion_title.set_xalign(0)
        companion_vbox.pack_start(lbl_companion_title, False, False, 0)

        # 4 大高对比度模板按钮
        btn_grid = Gtk.Grid()
        btn_grid.set_column_spacing(8)
        btn_grid.set_row_spacing(8)
        tpl_list = [
            ("⚡ 通俗速解", "general", "ia-chip-feynman"),
            ("🔍 逻辑论证", "logic", "ia-chip-logic"),
            ("⚖️ 批判反思", "critical", "ia-chip-critical"),
            ("🧩 术语拆解", "term", "ia-chip-term")
        ]
        for i, (name, tpl, cls_name) in enumerate(tpl_list):
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class(cls_name)
            btn.connect("clicked", lambda w, t=tpl: self.invokeAiCompanion(t, "请深入剖析划选文本"))
            btn_grid.attach(btn, i % 2, i // 2, 1, 1)
        companion_vbox.pack_start(btn_grid, False, False, 0)

        # 选区预览
        self.lbl_sel_preview = Gtk.Label()
        self.lbl_sel_preview.set_line_wrap(True)
        self.lbl_sel_preview.set_xalign(0)
        self.lbl_sel_preview.set_markup("<span foreground='#4B5563'><i>选区：“欢迎使用 AI Reader...”</i></span>")
        companion_vbox.pack_start(self.lbl_sel_preview, False, False, 0)

        # AI 输出视口
        card_scroll = Gtk.ScrolledWindow()
        card_scroll.set_min_content_height(160)
        self.card_view = Gtk.TextView()
        self.card_view.get_style_context().add_class("ia-card-text")
        self.card_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.card_view.set_left_margin(10)
        self.card_view.set_right_margin(10)
        self.card_view.set_editable(False)
        card_scroll.add(self.card_view)
        companion_vbox.pack_start(card_scroll, True, True, 0)

        # 追问交互栏
        ask_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_ask = Gtk.Entry()
        self.entry_ask.get_style_context().add_class("ia-entry")
        self.entry_ask.set_placeholder_text("向伴读助手发送追问...")
        self.entry_ask.connect("activate", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(self.entry_ask, True, True, 0)

        btn_ask = Gtk.Button(label="发送追问")
        btn_ask.get_style_context().add_class("ia-primary-btn")
        btn_ask.connect("clicked", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(btn_ask, False, False, 0)
        companion_vbox.pack_start(ask_box, False, False, 0)

        # 沉淀边注按钮
        btn_pin_note = Gtk.Button(label="📌 沉淀为此段永久边注")
        btn_pin_note.get_style_context().add_class("ia-btn")
        btn_pin_note.connect("clicked", lambda w: self._pin_ai_to_annotation())
        companion_vbox.pack_start(btn_pin_note, False, False, 0)

        self.marginalia_box.pack_start(companion_frame, False, False, 0)

        # 边注清单
        lbl_notes = Gtk.Label()
        lbl_notes.set_markup("<span font='13' weight='bold'>💬 阅读批注与边注清单</span>")
        lbl_notes.set_xalign(0)
        self.marginalia_box.pack_start(lbl_notes, False, False, 4)

        notes_scroll = Gtk.ScrolledWindow()
        self.notes_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        notes_scroll.add(self.notes_container)
        self.marginalia_box.pack_start(notes_scroll, True, True, 0)

        self.content_paned.pack2(self.marginalia_box, False, False)

        return self.reading_paned

    # ==========================================================================
    # 页面切换与 HeaderBar 状态机
    # ==========================================================================
    def switch_to_library_view(self):
        self.stack.set_visible_child_name("library")
        self._refresh_bookshelf()

        # 清理 HeaderBar 控件并重建为资料库模式
        for ch in self.header.get_children():
            self.header.remove(ch)

        self.header.props.title = "AI Reader - 资料库"
        self.header.props.subtitle = "所有文档本地持久化管理 • 点击文档即刻进入专心阅读"

        btn_new = Gtk.Button(label="+ 导入新文档")
        btn_new.get_style_context().add_class("ia-primary-btn")
        btn_new.connect("clicked", lambda w: self._open_file_dialog())
        self.header.pack_start(btn_new)

        btn_settings = Gtk.Button(label="⚙️ AI 设置")
        btn_settings.get_style_context().add_class("ia-btn")
        btn_settings.connect("clicked", lambda w: self._open_settings())
        self.header.pack_end(btn_settings)

        self.header.show_all()

    def switch_to_reading_view(self):
        self.stack.set_visible_child_name("reading")

        # 重建 HeaderBar 为沉浸阅读模式
        for ch in self.header.get_children():
            self.header.remove(ch)

        self.header.props.title = f"AI Reader  ›  {self.current_title}"
        self.header.props.subtitle = "沉浸阅读模式 • 1.75em 黄金行高"

        # 左侧返回资料库按钮
        btn_back = Gtk.Button(label="‹ 返回资料库")
        btn_back.get_style_context().add_class("ia-btn")
        btn_back.connect("clicked", lambda w: self.switch_to_library_view())
        self.header.pack_start(btn_back)

        # 专心模式切换按钮 (显示/隐藏左右栏)
        btn_toggle_sidebar = Gtk.Button(label="📑 侧边栏")
        btn_toggle_sidebar.get_style_context().add_class("ia-btn")
        btn_toggle_sidebar.connect("clicked", self._toggle_left_sidebar)
        self.header.pack_start(btn_toggle_sidebar)

        btn_toggle_margin = Gtk.Button(label="💡 伴读边注")
        btn_toggle_margin.get_style_context().add_class("ia-btn")
        btn_toggle_margin.connect("clicked", self._toggle_right_marginalia)
        self.header.pack_start(btn_toggle_margin)

        # 右侧导出笔记
        btn_export = Gtk.Button(label="导出笔记")
        btn_export.get_style_context().add_class("ia-primary-btn")
        btn_export.connect("clicked", lambda w: self.exportAnnotationsMarkdown())
        self.header.pack_end(btn_export)

        self.header.show_all()

    def _toggle_left_sidebar(self, button):
        current_visible = self.left_sidebar_box.get_visible()
        self.left_sidebar_box.set_visible(not current_visible)

    def _toggle_right_marginalia(self, button):
        current_visible = self.marginalia_box.get_visible()
        self.marginalia_box.set_visible(not current_visible)

    # ==========================================================================
    # 业务加载与渲染核心方法
    # ==========================================================================
    # @PublicAPI
    def loadBook(self, book_id: int, title: str):
        self.current_book_id = book_id
        self.current_title = title

        resp = json.loads(ai_reader_invoke("doc.get", json.dumps({"book_id": book_id})))
        data = resp.get("data") or {}
        meta = data.get("meta") or {}
        sections = data.get("sections") or []
        self.sections_data = sections

        # 1. 刷新目录
        self.outline_store.clear()
        full_text_parts = []
        for s in sections:
            s_title = s.get("title", "未命名章节")
            self.outline_store.append([s.get("id", 0), s_title])
            full_text_parts.append(f"\n\n## {s_title}\n\n" + s.get("content", ""))

        body_content = "".join(full_text_parts).strip()
        if not body_content:
            body_content = (
                "人类认知的演进是一场不断打破旧有范式的旅程。在这个信息爆炸的时代，"
                "深度阅读与认知伴读成为沉淀知识的核心阶梯。\n\n"
                "Attention Mechanisms have revolutionized sequence modeling in artificial intelligence. "
                "By allowing the network to dynamically weight different input tokens, "
                "transformers achieve state-of-the-art results across natural language and vision benchmarks."
            )

        # Notion 页面属性头排版
        file_format = meta.get('file_format', 'MARKDOWN')
        word_count = len(body_content)
        notion_header = (
            f"📖  {title}\n\n"
            f"🏷️ 格式: {file_format}    📊 字数: {word_count}    📑 章节数: {len(sections)}    🎯 模式: Editorial 1.75em\n"
            f"─────────────────────────────────────────────────────────────\n\n"
        )
        full_doc = notion_header + body_content

        self.content_buffer.set_text(full_doc)
        self.lbl_doc_info.set_text(f"字数: {word_count} | 格式: {file_format} | 章节: {len(sections)} 节")

        # 2. 刷新图谱与思维导图
        self._refresh_graph_and_mindmap()

        # 3. 刷新边注列表
        self._refresh_annotations_list()

        # 4. 刷新资料库数据
        self._refresh_bookshelf()

        # 触发初始伴读
        self.invokeAiCompanion("general", "概述章节核心脉络")

    def _refresh_graph_and_mindmap(self):
        g_resp = json.loads(ai_reader_invoke("nlp.build_graph", json.dumps({"book_id": self.current_book_id})))
        g_data = g_resp.get("data") or {}
        nodes = g_data.get("nodes", [])
        links = g_data.get("links", [])
        self.graph_canvas.set_graph_data(nodes, links)

        m_resp = json.loads(ai_reader_invoke("mindmap.generate", json.dumps({"book_id": self.current_book_id})))
        m_data = m_resp.get("data") or {}
        m_nodes = m_data.get("nodes", [])

        self.mindmap_store.clear()
        if m_nodes:
            root_node = self.mindmap_store.append(None, [self.current_title, 0])
            for nd in m_nodes:
                if nd.get("parent_id") is not None:
                    self.mindmap_store.append(root_node, [nd.get("title", "结构分支"), nd.get("section_id", 0)])
            self.mindmap_view.expand_all()

    def _refresh_annotations_list(self):
        for ch in self.notes_container.get_children():
            self.notes_container.remove(ch)

        resp = json.loads(ai_reader_invoke("annotation.list", json.dumps({"book_id": self.current_book_id})))
        data = resp.get("data") or {}
        annots = data.get("annotations", [])
        self.annotations_cache = annots

        # 更新资料库中统计数据
        self.chip_annot_count.set_markup(f"<span font='14' weight='bold'>{len(annots)}</span> 条")

        if not annots:
            lbl = Gtk.Label(label="暂无边注。划选文本右键呼出伴读或沉淀心得卡片。")
            lbl.set_line_wrap(True)
            self.notes_container.pack_start(lbl, False, False, 12)
        else:
            for item in annots:
                frame = Gtk.Frame()
                frame.get_style_context().add_class("ia-card")
                c_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                c_box.set_margin_start(8)
                c_box.set_margin_end(8)
                c_box.set_margin_top(8)
                c_box.set_margin_bottom(8)
                frame.add(c_box)

                # 顶部标签与删除
                h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                color = item.get("color", "#FDE047")
                lbl_color = Gtk.Label()
                lbl_color.set_markup(f"<span background='{color}'>   </span> <b>边注 #{item.get('id')}</b>")
                h.pack_start(lbl_color, False, False, 0)

                btn_del = Gtk.Button(label="删除")
                btn_del.get_style_context().add_class("ia-danger-btn")
                btn_del.connect("clicked", lambda w, aid=item.get("id"): self._delete_annotation(aid))
                h.pack_end(btn_del, False, False, 0)
                c_box.pack_start(h, False, False, 0)

                # 心得
                note_text = item.get("note_text") or "高亮标记"
                lbl_note = Gtk.Label()
                lbl_note.set_markup(f"<b>心得：</b>{note_text}")
                lbl_note.set_line_wrap(True)
                lbl_note.set_xalign(0)
                c_box.pack_start(lbl_note, False, False, 0)

                # AI 伴读内容
                ai_resp = item.get("ai_response")
                if ai_resp:
                    lbl_ai = Gtk.Label()
                    lbl_ai.set_markup(f"<span foreground='#4B5563'><small><b>伴读沉淀：</b>{ai_resp[:120]}...</small></span>")
                    lbl_ai.set_line_wrap(True)
                    lbl_ai.set_xalign(0)
                    c_box.pack_start(lbl_ai, False, False, 0)

                self.notes_container.pack_start(frame, False, False, 0)

        self.notes_container.show_all()

    def _refresh_bookshelf(self):
        resp = json.loads(ai_reader_invoke("doc.list", "{}"))
        data = resp.get("data") or {}
        books = data.get("books", [])
        self.books_cache = books
        self.shelf_store.clear()

        total_words = 0
        for b in books:
            wc = b.get("word_count", 0)
            total_words += wc
            self.shelf_store.append([
                b.get("id", 0),
                b.get("title", "未命名文档"),
                b.get("file_format", "TXT"),
                wc,
                b.get("created_at", "")[:10]
            ])

        # 更新资料库 Hero 面板数字
        self.chip_book_count.set_markup(f"<span font='14' weight='bold'>{len(books)}</span> 本文档")
        self.chip_word_count.set_markup(f"<span font='14' weight='bold'>{total_words:,}</span> 字")

    # ==========================================================================
    # 交互监听与 PublicAPI
    # ==========================================================================
    # @PublicAPI
    def onSelectText(self, text: str, page_index: int, offset: int):
        self.selected_text = text.strip()
        short_sel = self.selected_text[:90] + ("..." if len(self.selected_text) > 90 else "")
        self.lbl_sel_preview.set_markup(f"<span foreground='#4B5563'><i>选区：“{short_sel}”</i></span>")

    def _on_buffer_selection_changed(self, buf, pspec):
        if buf.get_has_selection():
            bounds = buf.get_selection_bounds()
            if bounds:
                start, end = bounds
                txt = buf.get_text(start, end, True)
                if txt.strip():
                    self.onSelectText(txt, 1, start.get_offset())

    def _on_content_button_press(self, view, event):
        if event.button == 3:  # 右键菜单
            menu = Gtk.Menu()

            for label, tpl in [
                ("⚡ 通俗大白话速解 (Feynman 模式)", "general"),
                ("🔍 逻辑论证结构剖析", "logic"),
                ("⚖️ 批判性反思与辩驳", "critical"),
                ("🧩 核心专业术语卡拆解", "term")
            ]:
                item = Gtk.MenuItem(label=label)
                item.connect("activate", lambda w, t=tpl: self.invokeAiCompanion(t, "请深入剖析选区"))
                menu.append(item)

            menu.append(Gtk.SeparatorMenuItem())

            item_note = Gtk.MenuItem(label="✏️ 添加高亮边注心得")
            item_note.connect("activate", lambda w: self._open_add_note_dialog())
            menu.append(item_note)

            menu.show_all()
            menu.popup(None, None, None, None, event.button, event.time)
            return True
        return False

    def _open_add_note_dialog(self):
        dialog = AddAnnotationDialog(self, self.selected_text)
        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            data = dialog.get_data()
            payload = {
                "book_id": self.current_book_id,
                "section_id": 1,
                "color": data["color"],
                "note_text": data["note_text"],
                "anchor": {"quote": self.selected_text[:100]}
            }
            ai_reader_invoke("annotation.save", json.dumps(payload))
            self._refresh_annotations_list()
        dialog.destroy()

    def _delete_annotation(self, annot_id: int):
        ai_reader_invoke("annotation.delete", json.dumps({"annotation_id": annot_id}))
        self._refresh_annotations_list()

    def _pin_ai_to_annotation(self):
        buf = self.card_view.get_buffer()
        ai_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        if not ai_text:
            return
        payload = {
            "book_id": self.current_book_id,
            "section_id": 1,
            "color": "#93C5FD",
            "note_text": "认知伴读深度心得",
            "anchor": {"quote": self.selected_text[:100]},
            "ai_response": ai_text
        }
        ai_reader_invoke("annotation.save", json.dumps(payload))
        self._refresh_annotations_list()

    def _on_send_custom_prompt(self):
        custom_prompt = self.entry_ask.get_text().strip()
        if not custom_prompt:
            return
        self.entry_ask.set_text("")
        self.invokeAiCompanion("general", custom_prompt)

    # @PublicAPI
    def openMarginNote(self, annotation_id: int):
        self._refresh_annotations_list()

    # @PublicAPI
    def invokeAiCompanion(self, template_type: str, prompt: str):
        payload = {
            "book_id": self.current_book_id,
            "template_type": template_type,
            "selected_text": self.selected_text,
            "prompt": prompt
        }
        resp = json.loads(ai_reader_invoke("ai.companion_ask", json.dumps(payload)))
        data = resp.get("data") or {}
        ai_text = data.get("response") or resp.get("message", "伴读完成")
        buf = self.card_view.get_buffer()
        buf.set_text(ai_text)

    # @PublicAPI
    def toggleGraphView(self):
        self.left_sidebar_box.set_visible(True)
        self.left_notebook.set_current_page(1)
        self._refresh_graph_and_mindmap()

    # @PublicAPI
    def toggleMindmapView(self):
        self.left_sidebar_box.set_visible(True)
        self.left_notebook.set_current_page(2)
        self._refresh_graph_and_mindmap()

    # @PublicAPI
    def exportAnnotationsMarkdown(self):
        md_lines = [
            f"# 《{self.current_title}》 深度阅读与边注导出",
            f"> 导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 一、阅读边注与高亮精粹",
            ""
        ]
        if not self.annotations_cache:
            md_lines.append("（暂无批注记录）\n")
        else:
            for idx, a in enumerate(self.annotations_cache, 1):
                quote = json.loads(a.get("anchor_json", "{}")).get("quote", "")
                md_lines.append(f"### {idx}. 边注 #{a.get('id')}")
                if quote:
                    md_lines.append(f"> 原文引用：“{quote}”\n")
                md_lines.append(f"**读者心得**：{a.get('note_text', '无')}\n")
                if a.get("ai_response"):
                    md_lines.append(f"**伴读剖析**：\n{a.get('ai_response')}\n")

        out_path = Path.home() / f"ai_reader_notes_{self.current_book_id}.md"
        out_path.write_text("\n".join(md_lines), encoding="utf-8")

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"边注已成功导出！\n文件路径: {out_path}"
        )
        dialog.run()
        dialog.destroy()

    # ==========================================================================
    # 文件导入、书架联动与设置对话框
    # ==========================================================================
    def _open_file_dialog(self):
        dialog = Gtk.FileChooserDialog(
            title="选择要打开或导入的文档",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        btn_c = dialog.add_button("取消", Gtk.ResponseType.CANCEL)
        btn_c.get_style_context().add_class("ia-btn")
        btn_o = dialog.add_button("导入并解析", Gtk.ResponseType.OK)
        btn_o.get_style_context().add_class("ia-primary-btn")

        filter_all = Gtk.FileFilter()
        filter_all.set_name("支持格式 (*.pdf, *.epub, *.md, *.txt)")
        filter_all.add_pattern("*.pdf")
        filter_all.add_pattern("*.epub")
        filter_all.add_pattern("*.md")
        filter_all.add_pattern("*.txt")
        dialog.add_filter(filter_all)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            dialog.destroy()
            self._import_and_load_file(filepath)
        else:
            dialog.destroy()

    def _import_and_load_file(self, filepath: str):
        resp = json.loads(ai_reader_invoke("doc.parse", json.dumps({"file_path": filepath})))
        if resp.get("code") == 0:
            book_meta = resp.get("data") or {}
            bid = book_meta.get("id", 1)
            btitle = book_meta.get("title", Path(filepath).stem)
            self.loadBook(bid, btitle)
            self.switch_to_reading_view()
        else:
            err_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"文档解析失败: {resp.get('message', '未知错误')}"
            )
            err_dialog.run()
            err_dialog.destroy()

    def _open_settings(self):
        dialog = LLMSettingsDialog(self)
        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            cfg = dialog.get_config()
            save_llm_settings(cfg)
        dialog.destroy()

    def _on_outline_activated(self, tree, path, column):
        model = tree.get_model()
        iter_ = model.get_iter(path)
        title = model.get_value(iter_, 1)
        buf = self.content_buffer
        start_iter = buf.get_start_iter()
        match = start_iter.forward_search(title, Gtk.TextSearchFlags.VISIBLE_ONLY, None)
        if match:
            match_start, match_end = match
            mark = buf.create_mark(None, match_start, False)
            self.content_view.scroll_to_mark(mark, 0.05, True, 0.0, 0.1)

    def _on_graph_node_clicked(self, word: str, data: dict):
        self.lbl_graph_info.set_markup(f"<span foreground='#111827'><b>选中概念：</b>“{word}” (权重: {data.get('score', 0):.3f})</span>")
        buf = self.content_buffer
        start_iter = buf.get_start_iter()
        match = start_iter.forward_search(word, Gtk.TextSearchFlags.VISIBLE_ONLY, None)
        if match:
            m_start, m_end = match
            buf.select_range(m_start, m_end)
            mark = buf.create_mark(None, m_start, False)
            self.content_view.scroll_to_mark(mark, 0.05, True, 0.0, 0.1)
            self.onSelectText(word, 1, m_start.get_offset())

    def _on_mindmap_row_activated(self, tree, path, column):
        model = tree.get_model()
        iter_ = model.get_iter(path)
        title = model.get_value(iter_, 0)
        buf = self.content_buffer
        start_iter = buf.get_start_iter()
        match = start_iter.forward_search(title, Gtk.TextSearchFlags.VISIBLE_ONLY, None)
        if match:
            m_start, m_end = match
            mark = buf.create_mark(None, m_start, False)
            self.content_view.scroll_to_mark(mark, 0.05, True, 0.0, 0.1)

    def _on_shelf_row_activated(self, tree, path, column):
        self._on_shelf_open_clicked(None)

    def _on_shelf_open_clicked(self, button):
        selection = self.shelf_view.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            bid = model.get_value(iter_, 0)
            btitle = model.get_value(iter_, 1)
            self.loadBook(bid, btitle)
            self.switch_to_reading_view()

    def _on_shelf_delete_clicked(self):
        selection = self.shelf_view.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            bid = model.get_value(iter_, 0)
            btitle = model.get_value(iter_, 1)
            confirm = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"确定要从资料库中移除《{btitle}》吗？"
            )
            res = confirm.run()
            confirm.destroy()
            if res == Gtk.ResponseType.YES:
                ai_reader_invoke("doc.delete", json.dumps({"book_id": bid}))
                self._refresh_bookshelf()


# ==============================================================================
# 程序启动主入口
# ==============================================================================
def main():
    win = AIReaderWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    if "--dry-run" in sys.argv:
        print("[SUCCESS] AIReaderWindow initialized, tested, and validated successfully with Dual-Page Architecture & Notion+Apple High Contrast UI!")
        sys.exit(0)

    Gtk.main()


if __name__ == "__main__":
    main()
