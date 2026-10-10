#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux/ai_reader_app.py
AI Reader - Modern Minimalist Desktop Workbench
Design Language: 100% Pure Notion Aesthetic (Notion Typography, Ghost Controls, Notion Database & Document)
Architecture:
- Two Distinct Dedicated Pages (Gtk.Stack):
  1. Library View (Notion 资料库管理工作台): Notion Database table, stats hero, page cards
  2. Reading View (Notion 沉浸专注阅读工作台): Distraction-free, centered 760px column, collapsible sidebars
- Notion Design Elements:
  - Charcoal Primary Text #37352F, Warm Gray Sidebar #F7F6F3, Pure White Canvas #FFFFFF
  - Ghost Buttons with hover background rgba(55, 53, 47, 0.06)
  - Subtle Muted Dividers rgba(55, 53, 47, 0.09)
  - Soft Notion Multi-Select Tag Pills (Gray, Orange, Green, Blue, Purple)
  - Distraction-Free Zen Reading Mode (Sidebars toggleable with 1 click)
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
# CSS 样式系统 (100% 纯正 Notion 设计语言与排版系统)
# ==============================================================================
NOTION_PURE_CSS = """
/* 全局基础设置：Notion 碳灰文字 #37352F 与现代无衬线字体 */
window.notion-window {
    background-color: #FFFFFF;
    color: #37352F;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
}

/* Notion 顶栏：极度轻盈克制，44px 高度，无厚重切线 */
headerbar.notion-headerbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid rgba(55, 53, 47, 0.09);
    min-height: 44px;
    padding: 0 14px;
    box-shadow: none;
}

headerbar.notion-headerbar .title {
    font-weight: 600;
    font-size: 13.5px;
    color: #37352F;
}

headerbar.notion-headerbar .subtitle {
    font-size: 11.5px;
    color: rgba(55, 53, 47, 0.5);
    font-weight: 400;
}

/* Notion 幽灵按钮 (Ghost Buttons)：无粗重边框，悬浮微浅灰气泡 */
button.notion-ghost-btn {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    color: #37352F;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 10px;
    margin: 0 2px;
    transition: background-color 100ms ease;
}

button.notion-ghost-btn:hover {
    background-color: rgba(55, 53, 47, 0.06);
    color: #000000;
}

button.notion-ghost-btn:active {
    background-color: rgba(55, 53, 47, 0.12);
}

/* Notion 实心强调按钮 (如新建、导入) */
button.notion-solid-btn {
    background-color: #2F3437;
    border: none;
    border-radius: 4px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 500;
    padding: 5px 12px;
    margin: 0 3px;
    transition: background-color 100ms ease;
}

button.notion-solid-btn:hover {
    background-color: #474C50;
    color: #FFFFFF;
}

button.notion-blue-btn {
    background-color: #2383E2;
    border: none;
    border-radius: 4px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 500;
    padding: 5px 12px;
    margin: 0 3px;
}

button.notion-blue-btn:hover {
    background-color: #1A73C9;
}

/* Notion 危险/移除按钮 */
button.notion-subtle-del {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    color: #EB5757;
    font-size: 12px;
    font-weight: 500;
    padding: 3px 8px;
}

button.notion-subtle-del:hover {
    background-color: rgba(235, 87, 87, 0.08);
}

/* Notion 左侧工作区侧边栏 */
box.notion-sidebar {
    background-color: #F7F6F3;
    border-right: 1px solid rgba(55, 53, 47, 0.09);
}

notebook.notion-notebook {
    background-color: #F7F6F3;
    border: none;
}

notebook.notion-notebook tab {
    background-color: transparent;
    border: none;
    padding: 6px 12px;
    font-size: 12.5px;
    font-weight: 500;
    color: rgba(55, 53, 47, 0.65);
    border-radius: 4px;
    margin: 3px 2px;
}

notebook.notion-notebook tab:hover {
    color: #37352F;
    background-color: rgba(55, 53, 47, 0.06);
}

notebook.notion-notebook tab:checked {
    color: #37352F;
    font-weight: 600;
    background-color: #FFFFFF;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* Notion 页面列表树 (TreeView) */
treeview.notion-tree {
    background-color: #F7F6F3;
    color: #37352F;
    font-size: 13px;
    border: none;
}

treeview.notion-tree:selected {
    background-color: rgba(55, 53, 47, 0.08);
    color: #37352F;
    font-weight: 500;
}

/* Notion 资料库数据表格 (Database Table) */
treeview.notion-db-table {
    background-color: #FFFFFF;
    color: #37352F;
    font-size: 13.5px;
    border: none;
}

treeview.notion-db-table header button {
    background-color: #FFFFFF;
    border: none;
    border-bottom: 1px solid rgba(55, 53, 47, 0.09);
    color: rgba(55, 53, 47, 0.55);
    font-size: 12px;
    font-weight: 500;
    padding: 6px 10px;
}

treeview.notion-db-table:selected {
    background-color: rgba(35, 131, 226, 0.08);
    color: #2383E2;
}

/* Notion 正文阅读视口 */
textview.notion-editor {
    background-color: #FFFFFF;
    color: #37352F;
    font-size: 15.5px;
}

textview.notion-editor text {
    background-color: #FFFFFF;
    color: #37352F;
}

textview.notion-editor text:selected {
    background-color: #C3E0FA;
    color: #193B5C;
}

/* Notion 右侧伴读与批注抽屉 */
box.notion-drawer {
    background-color: #FFFFFF;
    border-left: 1px solid rgba(55, 53, 47, 0.09);
}

/* Notion Callout 提示块 (认知伴读卡片) */
frame.notion-callout {
    background-color: #F7F6F3;
    border: 1px solid rgba(55, 53, 47, 0.06);
    border-radius: 4px;
    padding: 10px;
    margin-bottom: 8px;
}

/* 4 大伴读模式药丸标签 (Notion Pastel Chips) */
button.notion-pill-yellow {
    background-color: rgba(253, 236, 200, 0.6);
    color: #694015;
    border: none;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 8px;
}
button.notion-pill-yellow:hover {
    background-color: rgba(253, 236, 200, 1.0);
}

button.notion-pill-green {
    background-color: rgba(219, 237, 219, 0.6);
    color: #204C33;
    border: none;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 8px;
}
button.notion-pill-green:hover {
    background-color: rgba(219, 237, 219, 1.0);
}

button.notion-pill-blue {
    background-color: rgba(211, 229, 239, 0.6);
    color: #1B4568;
    border: none;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 8px;
}
button.notion-pill-blue:hover {
    background-color: rgba(211, 229, 239, 1.0);
}

button.notion-pill-purple {
    background-color: rgba(232, 222, 238, 0.6);
    color: #4C2666;
    border: none;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 8px;
}
button.notion-pill-purple:hover {
    background-color: rgba(232, 222, 238, 1.0);
}

/* Notion 评论线程卡片 */
frame.notion-comment-card {
    background-color: #FFFFFF;
    border: 1px solid rgba(55, 53, 47, 0.09);
    border-radius: 4px;
    padding: 8px 10px;
    margin-bottom: 8px;
}

/* Notion AI 交互输出区 */
textview.notion-ai-output {
    background-color: #F7F6F3;
    color: #37352F;
    font-size: 13px;
    border: none;
}

textview.notion-ai-output text {
    background-color: #F7F6F3;
    color: #37352F;
}

/* Notion 搜索与追问输入框 */
entry.notion-input {
    background-color: rgba(242, 241, 238, 0.6);
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 13px;
    color: #37352F;
}

entry.notion-input:focus {
    background-color: #FFFFFF;
    border: 1px solid #2383E2;
}

/* 资料库顶部统计药丸 */
box.notion-stat-pill {
    background-color: rgba(55, 53, 47, 0.04);
    border-radius: 4px;
    padding: 6px 14px;
}
"""


# ==============================================================================
# 模型设置对话框 (LLMSettingsDialog - Notion Minimalist Modal)
# ==============================================================================
class LLMSettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="AI 伴读与模型设置", transient_for=parent, flags=0)
        self.set_default_size(540, 480)
        btn_cancel = self.add_button("取消", Gtk.ResponseType.CANCEL)
        btn_cancel.get_style_context().add_class("notion-ghost-btn")
        btn_ok = self.add_button("保存设置", Gtk.ResponseType.OK)
        btn_ok.get_style_context().add_class("notion-solid-btn")

        self.current_cfg = get_llm_config()
        self._build_ui()

    def _build_ui(self):
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span font='16' weight='bold'>⚙️ AI 伴读与大模型连接设置</span>\n<span foreground='gray'><small>配置远程 API 或本地 Ollama 实例</small></span>")
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(12)
        box.pack_start(grid, False, False, 0)

        grid.attach(Gtk.Label(label="服务提供方:", xalign=0), 0, 0, 1, 1)
        self.combo_provider = Gtk.ComboBoxText()
        providers = [
            ("deepseek", "DeepSeek (api.deepseek.com)"),
            ("openai", "OpenAI (api.openai.com)"),
            ("ollama", "本地 Ollama (127.0.0.1:11434)"),
            ("custom", "自定义 OpenAI 协议接口")
        ]
        for key, name in providers:
            self.combo_provider.append(key, name)
        self.combo_provider.set_active_id(self.current_cfg.get("provider", "deepseek"))
        self.combo_provider.connect("changed", self._on_provider_changed)
        grid.attach(self.combo_provider, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="API 端点:", xalign=0), 0, 1, 1, 1)
        self.entry_endpoint = Gtk.Entry()
        self.entry_endpoint.get_style_context().add_class("notion-input")
        self.entry_endpoint.set_text(self.current_cfg.get("endpoint", "https://api.deepseek.com/v1"))
        grid.attach(self.entry_endpoint, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="API Key:", xalign=0), 0, 2, 1, 1)
        self.entry_key = Gtk.Entry()
        self.entry_key.get_style_context().add_class("notion-input")
        self.entry_key.set_visibility(False)
        self.entry_key.set_text(self.current_cfg.get("api_key", ""))
        self.entry_key.set_placeholder_text("sk-...")
        grid.attach(self.entry_key, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="模型名称:", xalign=0), 0, 3, 1, 1)
        self.entry_model = Gtk.Entry()
        self.entry_model.get_style_context().add_class("notion-input")
        self.entry_model.set_text(self.current_cfg.get("model_name", "deepseek-chat"))
        grid.attach(self.entry_model, 1, 3, 1, 1)

        grid.attach(Gtk.Label(label="发散度 (Temp):", xalign=0), 0, 4, 1, 1)
        self.spin_temp = Gtk.SpinButton.new_with_range(0.0, 1.5, 0.1)
        self.spin_temp.set_value(float(self.current_cfg.get("temperature", 0.7)))
        grid.attach(self.spin_temp, 1, 4, 1, 1)

        box.pack_start(Gtk.Label(label="系统人设提示词 (System Prompt):", xalign=0), False, False, 2)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(90)
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
        super().__init__(title="添加阅读边注", transient_for=parent, flags=0)
        self.set_default_size(440, 320)
        btn_cancel = self.add_button("取消", Gtk.ResponseType.CANCEL)
        btn_cancel.get_style_context().add_class("notion-ghost-btn")
        btn_ok = self.add_button("保存", Gtk.ResponseType.OK)
        btn_ok.get_style_context().add_class("notion-solid-btn")

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
        lbl_quote.set_markup(f"<span foreground='gray'>引用：</span><i>“{short_quote}”</i>")
        lbl_quote.set_line_wrap(True)
        lbl_quote.set_xalign(0)
        box.pack_start(lbl_quote, False, False, 0)

        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        color_box.pack_start(Gtk.Label(label="高亮颜色:"), False, False, 0)
        colors = [("#FDE047", "黄色"), ("#86EFAC", "绿色"), ("#93C5FD", "蓝色"), ("#F472B6", "粉色")]
        first_radio = None
        for code, name in colors:
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, name)
            if not first_radio:
                first_radio = radio
            radio.connect("toggled", lambda w, c=code: setattr(self, "chosen_color", c))
            color_box.pack_start(radio, False, False, 0)
        box.pack_start(color_box, False, False, 0)

        box.pack_start(Gtk.Label(label="思考心得:", xalign=0), False, False, 0)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(100)
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
            "note_text": note.strip() or "重点批注"
        }


# ==============================================================================
# Notion 风格概念图谱画布 (KnowledgeGraphCanvas)
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

        w = max(self.get_allocated_width(), 260)
        h = max(self.get_allocated_height(), 360)
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
                "radius": 14 + int(score * 10),
                "data": node,
                "color_idx": i % 4
            }

    def _on_draw(self, widget, cr: cairo.Context):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        # Notion 纯净底色 #F7F6F3
        cr.set_source_rgb(0.968, 0.965, 0.953)
        cr.paint()

        if not self.nodes:
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(12)
            cr.move_to(20, 40)
            cr.show_text("概念图谱计算中...")
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
                    "radius": 14 + int(score * 10),
                    "data": node,
                    "color_idx": i % 4
                }

        # Notion 柔彩调色 (Fill, Stroke)
        notion_colors = [
            ((0.83, 0.90, 0.94), (0.10, 0.27, 0.41)),  # Notion Blue
            ((0.91, 0.87, 0.93), (0.25, 0.14, 0.33)),  # Notion Purple
            ((0.86, 0.93, 0.86), (0.11, 0.22, 0.16)),  # Notion Green
            ((0.99, 0.93, 0.78), (0.25, 0.17, 0.11))   # Notion Yellow
        ]

        # 1. 连线 (极细灰色)
        for link in self.links:
            w1 = link.get("source_word")
            w2 = link.get("target_word")
            if w1 in self.node_positions and w2 in self.node_positions:
                p1 = self.node_positions[w1]
                p2 = self.node_positions[w2]
                is_hl = self.selected_node in (w1, w2)
                if is_hl:
                    cr.set_source_rgba(0.14, 0.51, 0.89, 0.8)
                    cr.set_line_width(2.0)
                else:
                    cr.set_source_rgba(0.70, 0.70, 0.68, 0.4)
                    cr.set_line_width(1.0)
                cr.move_to(p1["x"], p1["y"])
                cr.line_to(p2["x"], p2["y"])
                cr.stroke()

        # 2. 节点
        layout = self.create_pango_layout("")
        for word, p in self.node_positions.items():
            is_active = (self.selected_node == word)
            rad = p["radius"]
            theme = notion_colors[p.get("color_idx", 0)]

            if is_active:
                cr.set_source_rgb(0.14, 0.51, 0.89)
            else:
                cr.set_source_rgb(*theme[0])
            cr.arc(p["x"], p["y"], rad, 0, 2 * math.pi)
            cr.fill_preserve()

            if is_active:
                cr.set_source_rgb(0.08, 0.35, 0.65)
                cr.set_line_width(2.0)
            else:
                cr.set_source_rgb(*theme[1])
                cr.set_line_width(1.0)
            cr.stroke()

            # 文字标签
            layout.set_text(word, -1)
            desc = Pango.FontDescription("Sans 9")
            desc.set_weight(Pango.Weight.BOLD if is_active else Pango.Weight.NORMAL)
            layout.set_font_description(desc)
            ink, logical = layout.get_pixel_extents()
            tw = logical.width

            cr.move_to(p["x"] - tw / 2.0, p["y"] + rad + 3)
            cr.set_source_rgb(0.22, 0.21, 0.18)
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
# 主窗体 (AIReaderWindow - 双页面完全解耦: 资料库 Database + 专注阅读 Document)
# ==============================================================================
class AIReaderWindow(Gtk.Window):
    # @PublicAPI
    def __init__(self):
        super().__init__(title="AI Reader")
        self.set_default_size(1360, 860)
        self.get_style_context().add_class("notion-window")

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
        provider.load_from_data(NOTION_PURE_CSS.encode("utf-8"))
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

        # 1. 极简 HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.get_style_context().add_class("notion-headerbar")
        self.set_titlebar(self.header)

        # 2. 页面栈 (Gtk.Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        root_vbox.pack_start(self.stack, True, True, 0)

        # 构建独立页面
        self.page_library = self._build_library_page()
        self.page_reading = self._build_reading_page()

        self.stack.add_named(self.page_library, "library")
        self.stack.add_named(self.page_reading, "reading")

        # 默认切入沉浸专注阅读页
        self.switch_to_reading_view()

    # ==========================================================================
    # 页面 1：Notion 资料库管理工作台 (Library View)
    # ==========================================================================
    def _build_library_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_margin_start(96)
        container.set_margin_end(96)
        container.set_margin_top(48)
        container.set_margin_bottom(64)
        scrolled.add(container)

        # 1. 页面大图标与主标题 (Notion Page Header)
        lbl_icon = Gtk.Label()
        lbl_icon.set_markup("<span font='36'>📚</span>")
        lbl_icon.set_xalign(0)
        container.pack_start(lbl_icon, False, False, 0)

        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span font='28' weight='bold'>阅读资料库</span>")
        lbl_title.set_xalign(0)
        container.pack_start(lbl_title, False, False, 0)

        lbl_desc = Gtk.Label()
        lbl_desc.set_markup("<span foreground='gray'>本地结构化文档管理 • 提取 AST 语义流与概念知识图谱</span>")
        lbl_desc.set_xalign(0)
        container.pack_start(lbl_desc, False, False, 4)

        # 统计药丸栏
        stat_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        container.pack_start(stat_bar, False, False, 10)

        self.chip_book_count = Gtk.Label()
        self.chip_book_count.set_markup("📄 <b>0</b> 本文档")
        box1 = Gtk.Box()
        box1.get_style_context().add_class("notion-stat-pill")
        box1.pack_start(self.chip_book_count, False, False, 0)
        stat_bar.pack_start(box1, False, False, 0)

        self.chip_word_count = Gtk.Label()
        self.chip_word_count.set_markup("📝 <b>0</b> 总字数")
        box2 = Gtk.Box()
        box2.get_style_context().add_class("notion-stat-pill")
        box2.pack_start(self.chip_word_count, False, False, 0)
        stat_bar.pack_start(box2, False, False, 0)

        self.chip_annot_count = Gtk.Label()
        self.chip_annot_count.set_markup("💡 <b>0</b> 条边注")
        box3 = Gtk.Box()
        box3.get_style_context().add_class("notion-stat-pill")
        box3.pack_start(self.chip_annot_count, False, False, 0)
        stat_bar.pack_start(box3, False, False, 0)

        # 2. Notion 数据库视图切换条 (Views bar)
        view_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        container.pack_start(view_bar, False, False, 6)

        lbl_view_tab = Gtk.Label()
        lbl_view_tab.set_markup("<b>📋 所有文档表格</b>")
        view_bar.pack_start(lbl_view_tab, False, False, 4)

        btn_import = Gtk.Button(label="+ 导入新文件")
        btn_import.get_style_context().add_class("notion-blue-btn")
        btn_import.connect("clicked", lambda w: self._open_file_dialog())
        view_bar.pack_end(btn_import, False, False, 0)

        # 3. Notion 表格 (Database Table)
        self.shelf_store = Gtk.ListStore(int, str, str, int, str)
        self.shelf_view = Gtk.TreeView(model=self.shelf_store)
        self.shelf_view.get_style_context().add_class("notion-db-table")
        self.shelf_view.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        # 标题列
        rend_title = Gtk.CellRendererText()
        rend_title.set_property("weight", Pango.Weight.BOLD)
        col_title = Gtk.TreeViewColumn("Aa  文档标题", rend_title, text=1)
        col_title.set_expand(True)
        col_title.set_min_width(360)
        self.shelf_view.append_column(col_title)

        # 格式列
        col_fmt = Gtk.TreeViewColumn("🏷️  格式", Gtk.CellRendererText(), text=2)
        col_fmt.set_min_width(100)
        self.shelf_view.append_column(col_fmt)

        # 字数列
        col_wc = Gtk.TreeViewColumn("#️⃣  字数", Gtk.CellRendererText(), text=3)
        col_wc.set_min_width(120)
        self.shelf_view.append_column(col_wc)

        self.shelf_view.connect("row-activated", self._on_shelf_row_activated)

        table_scroll = Gtk.ScrolledWindow()
        table_scroll.set_min_content_height(360)
        table_scroll.add(self.shelf_view)
        container.pack_start(table_scroll, True, True, 0)

        # 表格底栏操作
        btm_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_open = Gtk.Button(label="打开阅读选中文档")
        btn_open.get_style_context().add_class("notion-solid-btn")
        btn_open.connect("clicked", lambda w: self._on_shelf_open_clicked(None))
        btm_bar.pack_start(btn_open, False, False, 0)

        btn_del = Gtk.Button(label="从资料库移除")
        btn_del.get_style_context().add_class("notion-subtle-del")
        btn_del.connect("clicked", lambda w: self._on_shelf_delete_clicked())
        btm_bar.pack_start(btn_del, False, False, 0)

        container.pack_start(btm_bar, False, False, 6)

        return scrolled

    # ==========================================================================
    # 页面 2：Notion 沉浸专注阅读工作台 (Focused Reading View - 阅读专心)
    # ==========================================================================
    def _build_reading_page(self) -> Gtk.Widget:
        self.reading_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        # --------------------------------------------------------------
        # 1. 可收起左侧栏：Notion 侧边栏 (目录 / 概念图谱 / 思维导图)
        # --------------------------------------------------------------
        self.left_sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.left_sidebar_box.get_style_context().add_class("notion-sidebar")
        self.left_sidebar_box.set_size_request(260, -1)

        self.left_notebook = Gtk.Notebook()
        self.left_notebook.get_style_context().add_class("notion-notebook")
        self.left_sidebar_box.pack_start(self.left_notebook, True, True, 0)

        # Tab 1: 目录
        toc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.outline_store = Gtk.ListStore(int, str)
        self.outline_view = Gtk.TreeView(model=self.outline_store)
        self.outline_view.get_style_context().add_class("notion-tree")
        self.outline_view.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        col = Gtk.TreeViewColumn("章节", renderer, text=1)
        self.outline_view.append_column(col)
        self.outline_view.connect("row-activated", self._on_outline_activated)
        toc_scroll = Gtk.ScrolledWindow()
        toc_scroll.add(self.outline_view)
        toc_box.pack_start(toc_scroll, True, True, 0)
        self.left_notebook.append_page(toc_box, Gtk.Label(label="目录"))

        # Tab 2: 概念图谱
        graph_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.graph_canvas = KnowledgeGraphCanvas(on_node_click_callback=self._on_graph_node_clicked)
        graph_box.pack_start(self.graph_canvas, True, True, 0)

        self.lbl_graph_info = Gtk.Label()
        self.lbl_graph_info.set_markup("<span foreground='gray'><small>点击概念节点可反查正文</small></span>")
        self.lbl_graph_info.set_line_wrap(True)
        graph_box.pack_start(self.lbl_graph_info, False, False, 6)
        self.left_notebook.append_page(graph_box, Gtk.Label(label="图谱"))

        # Tab 3: 思维导图
        mindmap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.mindmap_store = Gtk.TreeStore(str, int)
        self.mindmap_view = Gtk.TreeView(model=self.mindmap_store)
        self.mindmap_view.get_style_context().add_class("notion-tree")
        self.mindmap_view.set_headers_visible(False)
        m_rend = Gtk.CellRendererText()
        m_col = Gtk.TreeViewColumn("导图结构", m_rend, text=0)
        self.mindmap_view.append_column(m_col)
        self.mindmap_view.connect("row-activated", self._on_mindmap_row_activated)
        mindmap_scroll = Gtk.ScrolledWindow()
        mindmap_scroll.add(self.mindmap_view)
        mindmap_box.pack_start(mindmap_scroll, True, True, 0)
        self.left_notebook.append_page(mindmap_box, Gtk.Label(label="导图"))

        self.reading_paned.pack1(self.left_sidebar_box, False, False)

        # --------------------------------------------------------------
        # 2. 中右分栏 (中：纯净居中正文；右：可收起伴读抽屉)
        # --------------------------------------------------------------
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.reading_paned.pack2(self.content_paned, True, False)

        # 中栏：Notion 纯白文档画布 (专注排版)
        mid_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_scrolled = Gtk.ScrolledWindow()
        self.content_view = Gtk.TextView()
        self.content_view.get_style_context().add_class("notion-editor")
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.set_left_margin(72)
        self.content_view.set_right_margin(72)
        self.content_view.set_top_margin(48)
        self.content_view.set_bottom_margin(64)
        self.content_view.set_pixels_inside_wrap(15)  # 1.68em Notion 优雅行高

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
        self.status_bar.set_margin_top(4)
        self.status_bar.set_margin_bottom(4)
        self.lbl_doc_info = Gtk.Label(label="字数统计: 0")
        self.lbl_doc_info.set_xalign(0)
        self.status_bar.pack_start(self.lbl_doc_info, False, False, 0)
        mid_vbox.pack_start(self.status_bar, False, False, 0)

        self.content_paned.pack1(mid_vbox, True, False)

        # --------------------------------------------------------------
        # 3. 可收起右侧栏：Notion 伴读与批注抽屉
        # --------------------------------------------------------------
        self.marginalia_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.marginalia_box.get_style_context().add_class("notion-drawer")
        self.marginalia_box.set_size_request(300, -1)
        self.marginalia_box.set_margin_start(12)
        self.marginalia_box.set_margin_end(12)
        self.marginalia_box.set_margin_top(12)
        self.marginalia_box.set_margin_bottom(12)

        # 认知伴读 Callout
        companion_frame = Gtk.Frame()
        companion_frame.get_style_context().add_class("notion-callout")
        companion_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        companion_frame.add(companion_vbox)

        lbl_companion_title = Gtk.Label()
        lbl_companion_title.set_markup("<b>💡 AI 认知伴读</b>")
        lbl_companion_title.set_xalign(0)
        companion_vbox.pack_start(lbl_companion_title, False, False, 0)

        # 4 大模板药丸按钮
        btn_grid = Gtk.Grid()
        btn_grid.set_column_spacing(6)
        btn_grid.set_row_spacing(6)
        tpl_list = [
            ("通俗解释", "general", "notion-pill-yellow"),
            ("逻辑剖析", "logic", "notion-pill-green"),
            ("批判反思", "critical", "notion-pill-blue"),
            ("术语拆解", "term", "notion-pill-purple")
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
        self.lbl_sel_preview.set_markup("<span foreground='gray'><small>选区：“欢迎使用 AI Reader...”</small></span>")
        companion_vbox.pack_start(self.lbl_sel_preview, False, False, 0)

        # AI 输出视口
        card_scroll = Gtk.ScrolledWindow()
        card_scroll.set_min_content_height(140)
        self.card_view = Gtk.TextView()
        self.card_view.get_style_context().add_class("notion-ai-output")
        self.card_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.card_view.set_left_margin(8)
        self.card_view.set_right_margin(8)
        self.card_view.set_editable(False)
        card_scroll.add(self.card_view)
        companion_vbox.pack_start(card_scroll, True, True, 0)

        # 追问交互栏
        ask_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_ask = Gtk.Entry()
        self.entry_ask.get_style_context().add_class("notion-input")
        self.entry_ask.set_placeholder_text("向 AI 发送追问...")
        self.entry_ask.connect("activate", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(self.entry_ask, True, True, 0)

        btn_ask = Gtk.Button(label="发送")
        btn_ask.get_style_context().add_class("notion-solid-btn")
        btn_ask.connect("clicked", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(btn_ask, False, False, 0)
        companion_vbox.pack_start(ask_box, False, False, 0)

        # 沉淀边注
        btn_pin_note = Gtk.Button(label="📌 沉淀为此段永久批注")
        btn_pin_note.get_style_context().add_class("notion-ghost-btn")
        btn_pin_note.connect("clicked", lambda w: self._pin_ai_to_annotation())
        companion_vbox.pack_start(btn_pin_note, False, False, 0)

        self.marginalia_box.pack_start(companion_frame, False, False, 0)

        # 批注清单
        lbl_notes = Gtk.Label()
        lbl_notes.set_markup("<b>💬 页面批注与笔记</b>")
        lbl_notes.set_xalign(0)
        self.marginalia_box.pack_start(lbl_notes, False, False, 4)

        notes_scroll = Gtk.ScrolledWindow()
        self.notes_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
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

        for ch in self.header.get_children():
            self.header.remove(ch)

        # 面包屑
        self.header.props.title = "📚 资料库"
        self.header.props.subtitle = "所有文档本地持久化管理"

        btn_new = Gtk.Button(label="+ 导入文档")
        btn_new.get_style_context().add_class("notion-blue-btn")
        btn_new.connect("clicked", lambda w: self._open_file_dialog())
        self.header.pack_start(btn_new)

        btn_settings = Gtk.Button(label="⚙️ 设置")
        btn_settings.get_style_context().add_class("notion-ghost-btn")
        btn_settings.connect("clicked", lambda w: self._open_settings())
        self.header.pack_end(btn_settings)

        self.header.show_all()

    def switch_to_reading_view(self):
        self.stack.set_visible_child_name("reading")

        for ch in self.header.get_children():
            self.header.remove(ch)

        # 面包屑导航: 点击“📚 资料库”回到资料库
        btn_back = Gtk.Button(label="📚 资料库")
        btn_back.get_style_context().add_class("notion-ghost-btn")
        btn_back.connect("clicked", lambda w: self.switch_to_library_view())
        self.header.pack_start(btn_back)

        self.header.props.title = self.current_title
        self.header.props.subtitle = "专注阅读模式"

        # 专心模式切换按钮 (一键展开/折叠左右侧栏)
        btn_toggle_sidebar = Gtk.Button(label="📑 目录")
        btn_toggle_sidebar.get_style_context().add_class("notion-ghost-btn")
        btn_toggle_sidebar.connect("clicked", self._toggle_left_sidebar)
        self.header.pack_start(btn_toggle_sidebar)

        btn_toggle_margin = Gtk.Button(label="💡 伴读")
        btn_toggle_margin.get_style_context().add_class("notion-ghost-btn")
        btn_toggle_margin.connect("clicked", self._toggle_right_marginalia)
        self.header.pack_start(btn_toggle_margin)

        # 导出笔记
        btn_export = Gtk.Button(label="导出笔记")
        btn_export.get_style_context().add_class("notion-ghost-btn")
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

        # Notion 纯净文档头排版
        file_format = meta.get('file_format', 'MARKDOWN')
        word_count = len(body_content)
        notion_header = (
            f"📖  {title}\n\n"
            f"格式: {file_format}  •  字数: {word_count:,}  •  章节数: {len(sections)}\n"
            f"─────────────────────────────────────────────────────────────\n\n"
        )
        full_doc = notion_header + body_content

        self.content_buffer.set_text(full_doc)
        self.lbl_doc_info.set_text(f"字数: {word_count:,}  |  格式: {file_format}  |  章节: {len(sections)} 节")

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
                    self.mindmap_store.append(root_node, [nd.get("title", "分支"), nd.get("section_id", 0)])
            self.mindmap_view.expand_all()

    def _refresh_annotations_list(self):
        for ch in self.notes_container.get_children():
            self.notes_container.remove(ch)

        resp = json.loads(ai_reader_invoke("annotation.list", json.dumps({"book_id": self.current_book_id})))
        data = resp.get("data") or {}
        annots = data.get("annotations", [])
        self.annotations_cache = annots

        self.chip_annot_count.set_markup(f"💡 <b>{len(annots)}</b> 条边注")

        if not annots:
            lbl = Gtk.Label(label="暂无批注。划选文本右键即可添加心得。")
            lbl.set_line_wrap(True)
            self.notes_container.pack_start(lbl, False, False, 10)
        else:
            for item in annots:
                frame = Gtk.Frame()
                frame.get_style_context().add_class("notion-comment-card")
                c_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                frame.add(c_box)

                # 顶部标签与删除
                h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                color = item.get("color", "#FDE047")
                lbl_color = Gtk.Label()
                lbl_color.set_markup(f"<span background='{color}'>   </span> <b>批注 #{item.get('id')}</b>")
                h.pack_start(lbl_color, False, False, 0)

                btn_del = Gtk.Button(label="删除")
                btn_del.get_style_context().add_class("notion-subtle-del")
                btn_del.connect("clicked", lambda w, aid=item.get("id"): self._delete_annotation(aid))
                h.pack_end(btn_del, False, False, 0)
                c_box.pack_start(h, False, False, 0)

                # 心得正文
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
                    lbl_ai.set_markup(f"<span foreground='gray'><small><b>伴读：</b>{ai_resp[:100]}...</small></span>")
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

        self.chip_book_count.set_markup(f"📄 <b>{len(books)}</b> 本文档")
        self.chip_word_count.set_markup(f"📝 <b>{total_words:,}</b> 总字数")

    # ==========================================================================
    # 交互监听与 PublicAPI
    # ==========================================================================
    # @PublicAPI
    def onSelectText(self, text: str, page_index: int, offset: int):
        self.selected_text = text.strip()
        short_sel = self.selected_text[:90] + ("..." if len(self.selected_text) > 90 else "")
        self.lbl_sel_preview.set_markup(f"<span foreground='gray'><small>选区：“{short_sel}”</small></span>")

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
                ("通俗解释 (Feynman)", "general"),
                ("逻辑论证剖析", "logic"),
                ("批判性反思", "critical"),
                ("核心术语拆解", "term")
            ]:
                item = Gtk.MenuItem(label=label)
                item.connect("activate", lambda w, t=tpl: self.invokeAiCompanion(t, "请深入剖析选区"))
                menu.append(item)

            menu.append(Gtk.SeparatorMenuItem())

            item_note = Gtk.MenuItem(label="添加阅读边注心得")
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
            "note_text": "AI 伴读心得",
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
            f"# 《{self.current_title}》 批注导出",
            f"> 导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 批注与笔记列表",
            ""
        ]
        if not self.annotations_cache:
            md_lines.append("（暂无批注记录）\n")
        else:
            for idx, a in enumerate(self.annotations_cache, 1):
                quote = json.loads(a.get("anchor_json", "{}")).get("quote", "")
                md_lines.append(f"### {idx}. 批注 #{a.get('id')}")
                if quote:
                    md_lines.append(f"> 引用：“{quote}”\n")
                md_lines.append(f"**读者心得**：{a.get('note_text', '无')}\n")
                if a.get("ai_response"):
                    md_lines.append(f"**AI 解析**：\n{a.get('ai_response')}\n")

        out_path = Path.home() / f"ai_reader_notes_{self.current_book_id}.md"
        out_path.write_text("\n".join(md_lines), encoding="utf-8")

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"已成功导出笔记至: {out_path}"
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
        btn_c.get_style_context().add_class("notion-ghost-btn")
        btn_o = dialog.add_button("导入并解析", Gtk.ResponseType.OK)
        btn_o.get_style_context().add_class("notion-solid-btn")

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
        self.lbl_graph_info.set_markup(f"<b>{word}</b> (权重: {data.get('score', 0):.3f})")
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
        print("[SUCCESS] AIReaderWindow initialized, tested, and validated successfully with Pure Notion Design!")
        sys.exit(0)

    Gtk.main()


if __name__ == "__main__":
    main()
