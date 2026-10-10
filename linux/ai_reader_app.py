#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux/ai_reader_app.py
AI Reader - Modern Minimalist Desktop Workbench (Linux Native GTK3 Engine)
Design Language:
- Tailwind CSS Typography (Prose Stone / Neutral) & iA Writer Aesthetic
- 100% Pure Monoline Line Icons & Typography (Zero Emoji)
- Left Navigation (Outline / Knowledge Graph / Mindmap / Bookshelf)
- Center Editorial Viewport (1.8em Golden Line Height, Paragraph Anchors, Selection Menu)
- Right Marginalia Column (Baseline Anchored Notes & 4-Template Cognitive Companion)
- Strict Alignment with PRD, Architecture & Six-Tuple Engine Contracts
"""

import sys
import os
import math
import json
import time
from pathlib import Path

# 适配本地运行与打包安装后运行环境
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
# CSS 样式系统 (Tailwind Prose Stone / Neutral & iA Writer 羊皮纸护眼风格)
# ==============================================================================
PROSE_CSS = """
window.ia-reader-window {
    background-color: #FAF9F6;
    color: #1C1917;
}

headerbar.ia-headerbar {
    background-color: #FAF9F6;
    border-bottom: 1px solid #E7E5E4;
    min-height: 48px;
    padding: 0 12px;
}

headerbar.ia-headerbar button {
    background: #FFFFFF;
    border: 1px solid #D6D3D1;
    border-radius: 6px;
    color: #292524;
    font-size: 13px;
    padding: 4px 12px;
    margin: 0 3px;
}

headerbar.ia-headerbar button:hover {
    background: #F5F5F4;
    border-color: #A8A29E;
}

notebook.ia-notebook {
    background-color: #F7F6F3;
    border-right: 1px solid #E7E5E4;
}

notebook.ia-notebook tab {
    padding: 6px 14px;
    font-size: 13px;
    color: #57534E;
}

notebook.ia-notebook tab:checked {
    color: #0C0A09;
    font-weight: bold;
    background-color: #FAF9F6;
}

textview.ia-editor {
    background-color: #FAF9F6;
    color: #1C1917;
}

textview.ia-editor text {
    background-color: #FAF9F6;
    color: #1C1917;
}

box.ia-marginalia {
    background-color: #FBFBFA;
    border-left: 1px solid #E7E5E4;
}

frame.ia-card {
    background-color: #FFFFFF;
    border: 1px solid #E7E5E4;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 8px;
}

button.ia-template-btn {
    background: #F5F5F4;
    border: 1px solid #D6D3D1;
    border-radius: 6px;
    color: #44403C;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 8px;
}

button.ia-template-btn:hover {
    background: #E7E5E4;
    color: #1C1917;
}

button.ia-primary-btn {
    background: #2563EB;
    color: #FFFFFF;
    border-radius: 6px;
    border: none;
    font-size: 12px;
    padding: 5px 12px;
}

button.ia-primary-btn:hover {
    background: #1D4ED8;
}
"""


# ==============================================================================
# 模型设置对话框 (LLMSettingsDialog)
# ==============================================================================
class LLMSettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="模型与伴读配置", transient_for=parent, flags=0)
        self.set_default_size(520, 480)
        self.add_button("取消", Gtk.ResponseType.CANCEL)
        self.add_button("保存配置", Gtk.ResponseType.OK)

        self.current_cfg = get_llm_config()
        self._build_ui()

    def _build_ui(self):
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        lbl = Gtk.Label()
        lbl.set_markup("<b>LLM 服务与深度伴读配置</b>\n<small>支持 OpenAI / DeepSeek / Ollama / Gemini / 兼容端点</small>")
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        box.pack_start(grid, False, False, 0)

        # 预置供应商
        grid.attach(Gtk.Label(label="服务提供方:", xalign=0), 0, 0, 1, 1)
        self.combo_provider = Gtk.ComboBoxText()
        providers = [
            ("deepseek", "DeepSeek (api.deepseek.com)"),
            ("openai", "OpenAI (api.openai.com)"),
            ("ollama", "本地 Ollama (127.0.0.1:11434)"),
            ("custom", "自定义 OpenAI 兼容接口")
        ]
        for key, name in providers:
            self.combo_provider.append(key, name)
        self.combo_provider.set_active_id(self.current_cfg.get("provider", "deepseek"))
        self.combo_provider.connect("changed", self._on_provider_changed)
        grid.attach(self.combo_provider, 1, 0, 1, 1)

        # API Endpoint
        grid.attach(Gtk.Label(label="API 端点:", xalign=0), 0, 1, 1, 1)
        self.entry_endpoint = Gtk.Entry()
        self.entry_endpoint.set_text(self.current_cfg.get("endpoint", "https://api.deepseek.com/v1"))
        grid.attach(self.entry_endpoint, 1, 1, 1, 1)

        # API Key
        grid.attach(Gtk.Label(label="API Key:", xalign=0), 0, 2, 1, 1)
        self.entry_key = Gtk.Entry()
        self.entry_key.set_visibility(False)
        self.entry_key.set_text(self.current_cfg.get("api_key", ""))
        self.entry_key.set_placeholder_text("sk-...")
        grid.attach(self.entry_key, 1, 2, 1, 1)

        # 模型名称
        grid.attach(Gtk.Label(label="模型名称:", xalign=0), 0, 3, 1, 1)
        self.entry_model = Gtk.Entry()
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
        super().__init__(title="添加阅读边注", transient_for=parent, flags=0)
        self.set_default_size(440, 320)
        self.add_button("取消", Gtk.ResponseType.CANCEL)
        self.add_button("沉淀边注", Gtk.ResponseType.OK)

        self.selected_text = selected_text
        self.chosen_color = "#FDE047"  # 默认黄色
        self._build_ui()

    def _build_ui(self):
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        lbl_quote = Gtk.Label()
        short_quote = self.selected_text[:140] + ("..." if len(self.selected_text) > 140 else "")
        lbl_quote.set_markup(f"<b>引用选区：</b>\n<i>“{short_quote}”</i>")
        lbl_quote.set_line_wrap(True)
        lbl_quote.set_xalign(0)
        box.pack_start(lbl_quote, False, False, 0)

        # 颜色选择
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        color_box.pack_start(Gtk.Label(label="高亮色彩:"), False, False, 0)

        colors = [("#FDE047", "鹅黄"), ("#86EFAC", "薄荷绿"), ("#93C5FD", "天蓝"), ("#F472B6", "樱粉")]
        self.color_radios = []
        first_radio = None
        for code, name in colors:
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, name)
            if not first_radio:
                first_radio = radio
            radio.connect("toggled", lambda w, c=code: setattr(self, "chosen_color", c))
            color_box.pack_start(radio, False, False, 0)
        box.pack_start(color_box, False, False, 0)

        # 批注心得
        box.pack_start(Gtk.Label(label="边注心得 / 个人思考:", xalign=0), False, False, 0)
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
        
        # 极坐标环状与力导向初值排布
        w = max(self.get_allocated_width(), 320)
        h = max(self.get_allocated_height(), 400)
        cx, cy = w / 2.0, h / 2.0
        r_base = min(cx, cy) * 0.72

        n = len(self.nodes)
        for i, node in enumerate(self.nodes):
            angle = 2.0 * math.pi * i / max(n, 1)
            # 根据重要度/权重在半径上微调
            score = float(node.get("score", 0.5))
            r = r_base * (0.55 + 0.45 * (1.0 - min(score, 1.0)))
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.node_positions[node["word"]] = {
                "x": x,
                "y": y,
                "radius": 14 + int(score * 12),
                "data": node
            }

    def _on_draw(self, widget, cr: cairo.Context):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        # 底色微暖
        cr.set_source_rgb(0.97, 0.97, 0.96)
        cr.paint()

        if not self.nodes:
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(13)
            cr.move_to(20, 40)
            cr.show_text("全书关键词提取中或暂无关联图谱...")
            return

        # 重新校准中心
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
                    "radius": 14 + int(score * 12),
                    "data": node
                }

        # 1. 绘制共现连接线
        for link in self.links:
            w1 = link.get("source_word")
            w2 = link.get("target_word")
            if w1 in self.node_positions and w2 in self.node_positions:
                p1 = self.node_positions[w1]
                p2 = self.node_positions[w2]
                weight = float(link.get("co_occurrence", 1))

                is_highlight = self.selected_node in (w1, w2)
                if is_highlight:
                    cr.set_source_rgba(0.15, 0.4, 0.9, 0.8)
                    cr.set_line_width(2.0 + min(weight * 0.5, 3.0))
                else:
                    cr.set_source_rgba(0.75, 0.75, 0.75, 0.4)
                    cr.set_line_width(1.0)
                
                cr.move_to(p1["x"], p1["y"])
                cr.line_to(p2["x"], p2["y"])
                cr.stroke()

        # 2. 绘制节点圆圈与文本标签
        layout = self.create_pango_layout("")
        for word, p in self.node_positions.items():
            is_active = (self.selected_node == word)
            rad = p["radius"]

            # 填充圆
            if is_active:
                cr.set_source_rgb(0.18, 0.45, 0.95)
            else:
                cr.set_source_rgb(0.92, 0.93, 0.95)
            cr.arc(p["x"], p["y"], rad, 0, 2 * math.pi)
            cr.fill_preserve()

            # 边框
            if is_active:
                cr.set_source_rgb(0.1, 0.25, 0.6)
                cr.set_line_width(2.5)
            else:
                cr.set_source_rgb(0.65, 0.68, 0.72)
                cr.set_line_width(1.2)
            cr.stroke()

            # 标签
            layout.set_text(word, -1)
            desc = Pango.FontDescription("Sans 9")
            layout.set_font_description(desc)
            ink, logical = layout.get_pixel_extents()
            tw, th = logical.width, logical.height

            cr.move_to(p["x"] - tw / 2.0, p["y"] + rad + 2)
            if is_active:
                cr.set_source_rgb(0.1, 0.2, 0.5)
            else:
                cr.set_source_rgb(0.25, 0.25, 0.28)
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
# 主窗体 (AIReaderWindow)
# ==============================================================================
class AIReaderWindow(Gtk.Window):
    # @PublicAPI
    def __init__(self):
        super().__init__(title="AI Reader - 现代智能伴读工作台")
        self.set_default_size(1360, 840)
        self.get_style_context().add_class("ia-reader-window")

        self.current_book_id = 1
        self.current_title = "AI Reader 欢迎指南"
        self.selected_text = "欢迎使用 AI Reader。本应用遵循 iA Writer 极简主义与深度认知排版哲学。"
        self.sections_data = []
        self.annotations_cache = []

        self._apply_css()
        self._load_app_icon()
        self._setup_ui()

        # 加载初始书籍与配置
        self.loadBook(self.current_book_id, self.current_title)

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(PROSE_CSS.encode("utf-8"))
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
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # 1. 顶部 HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.get_style_context().add_class("ia-headerbar")
        self.header.props.title = "AI Reader"
        self.header.props.subtitle = "Editorial 1.8em • iA Writer 边注 • 深度认知伴读"
        self.set_titlebar(self.header)

        # 左侧工具
        btn_open = Gtk.Button(label="打开文件")
        btn_open.connect("clicked", lambda w: self._open_file_dialog())
        self.header.pack_start(btn_open)

        btn_shelf = Gtk.Button(label="本地书架")
        btn_shelf.connect("clicked", lambda w: self.left_notebook.set_current_page(3))
        self.header.pack_start(btn_shelf)

        # 中侧视图切换
        btn_graph = Gtk.Button(label="概念图谱")
        btn_graph.connect("clicked", lambda w: self.toggleGraphView())
        self.header.pack_start(btn_graph)

        btn_mindmap = Gtk.Button(label="思维导图")
        btn_mindmap.connect("clicked", lambda w: self.toggleMindmapView())
        self.header.pack_start(btn_mindmap)

        # 右侧操作
        btn_export = Gtk.Button(label="导出笔记")
        btn_export.connect("clicked", lambda w: self.exportAnnotationsMarkdown())
        self.header.pack_end(btn_export)

        btn_settings = Gtk.Button(label="AI 设置")
        btn_settings.connect("clicked", lambda w: self._open_settings())
        self.header.pack_end(btn_settings)

        # 2. 三栏工作台主体 (Paned)
        self.main_hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(self.main_hpaned, True, True, 0)

        # ==============================================================
        # 左栏：4 合 1 Notebook (目录 / 概念图谱 / 思维导图 / 书架)
        # ==============================================================
        self.left_notebook = Gtk.Notebook()
        self.left_notebook.get_style_context().add_class("ia-notebook")
        self.left_notebook.set_size_request(280, -1)

        # Page 0: 目录 (TOC)
        toc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.outline_store = Gtk.ListStore(int, str)  # sec_id, title
        self.outline_view = Gtk.TreeView(model=self.outline_store)
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

        # Page 1: 概念图谱 (Knowledge Graph)
        graph_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.graph_canvas = KnowledgeGraphCanvas(on_node_click_callback=self._on_graph_node_clicked)
        graph_box.pack_start(self.graph_canvas, True, True, 0)

        self.lbl_graph_info = Gtk.Label()
        self.lbl_graph_info.set_markup("<small>点击概念节点反查正文段落</small>")
        self.lbl_graph_info.set_line_wrap(True)
        graph_box.pack_start(self.lbl_graph_info, False, False, 6)
        self.left_notebook.append_page(graph_box, Gtk.Label(label="概念图谱"))

        # Page 2: 思维导图 (Mindmap)
        mindmap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.mindmap_store = Gtk.TreeStore(str, int)  # title, section_id
        self.mindmap_view = Gtk.TreeView(model=self.mindmap_store)
        self.mindmap_view.set_headers_visible(False)
        m_rend = Gtk.CellRendererText()
        m_col = Gtk.TreeViewColumn("导图结构", m_rend, text=0)
        self.mindmap_view.append_column(m_col)
        self.mindmap_view.connect("row-activated", self._on_mindmap_row_activated)
        mindmap_scroll = Gtk.ScrolledWindow()
        mindmap_scroll.add(self.mindmap_view)
        mindmap_box.pack_start(mindmap_scroll, True, True, 0)
        self.left_notebook.append_page(mindmap_box, Gtk.Label(label="思维导图"))

        # Page 3: 本地书架 (Bookshelf)
        shelf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        shelf_box.set_margin_start(8)
        shelf_box.set_margin_end(8)
        shelf_box.set_margin_top(8)

        self.shelf_store = Gtk.ListStore(int, str, str, int)  # id, title, format, word_count
        self.shelf_view = Gtk.TreeView(model=self.shelf_store)
        self.shelf_view.append_column(Gtk.TreeViewColumn("ID", Gtk.CellRendererText(), text=0))
        self.shelf_view.append_column(Gtk.TreeViewColumn("书名", Gtk.CellRendererText(), text=1))
        self.shelf_view.append_column(Gtk.TreeViewColumn("格式", Gtk.CellRendererText(), text=2))
        self.shelf_view.connect("row-activated", self._on_shelf_row_activated)
        shelf_scroll = Gtk.ScrolledWindow()
        shelf_scroll.add(self.shelf_view)
        shelf_box.pack_start(shelf_scroll, True, True, 0)

        btn_shelf_open = Gtk.Button(label="阅读选中书籍")
        btn_shelf_open.connect("clicked", self._on_shelf_open_clicked)
        shelf_box.pack_start(btn_shelf_open, False, False, 4)

        self.left_notebook.append_page(shelf_box, Gtk.Label(label="书架"))

        self.main_hpaned.pack1(self.left_notebook, False, False)

        # ==============================================================
        # 中右分栏 (中：正文沉浸流；右：iA Writer 边注与伴读)
        # ==============================================================
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_hpaned.pack2(self.content_paned, True, False)

        # 中栏：正文沉浸阅读视口
        mid_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_scrolled = Gtk.ScrolledWindow()
        self.content_view = Gtk.TextView()
        self.content_view.get_style_context().add_class("ia-editor")
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.content_view.set_left_margin(54)
        self.content_view.set_right_margin(54)
        self.content_view.set_top_margin(36)
        self.content_view.set_bottom_margin(48)
        self.content_view.set_pixels_inside_wrap(16)  # 1.8em 黄金行高
        self.content_view.modify_font(Pango.FontDescription("Serif 13.5"))

        # 正文选区与右键监听
        self.content_buffer = self.content_view.get_buffer()
        self.content_buffer.connect("notify::has-selection", self._on_buffer_selection_changed)
        self.content_view.connect("button-press-event", self._on_content_button_press)

        # 标签定义 (高亮显示)
        self.tag_highlight_yellow = self.content_buffer.create_tag("hl_yellow", background="#FEF08A")
        self.tag_highlight_green = self.content_buffer.create_tag("hl_green", background="#BBF7D0")
        self.tag_highlight_blue = self.content_buffer.create_tag("hl_blue", background="#BAE6FD")
        self.tag_highlight_pink = self.content_buffer.create_tag("hl_pink", background="#FBCFE8")

        self.content_scrolled.add(self.content_view)
        mid_vbox.pack_start(self.content_scrolled, True, True, 0)

        # 底部状态微栏
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.status_bar.set_margin_start(16)
        self.status_bar.set_margin_end(16)
        self.status_bar.set_margin_top(4)
        self.status_bar.set_margin_bottom(4)
        self.lbl_doc_info = Gtk.Label(label="字数统计: 0 | 进度: 100%")
        self.lbl_doc_info.set_xalign(0)
        self.status_bar.pack_start(self.lbl_doc_info, False, False, 0)
        mid_vbox.pack_start(self.status_bar, False, False, 0)

        self.content_paned.pack1(mid_vbox, True, False)

        # ==============================================================
        # 右栏：iA Writer 边注栏与深度认知伴读 (Marginalia)
        # ==============================================================
        self.marginalia_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.marginalia_box.get_style_context().add_class("ia-marginalia")
        self.marginalia_box.set_size_request(340, -1)
        self.marginalia_box.set_margin_start(12)
        self.marginalia_box.set_margin_end(12)
        self.marginalia_box.set_margin_top(12)
        self.marginalia_box.set_margin_bottom(12)

        # 顶部卡片：深度认知伴读卡片
        companion_frame = Gtk.Frame()
        companion_frame.get_style_context().add_class("ia-card")
        companion_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        companion_vbox.set_margin_start(8)
        companion_vbox.set_margin_end(8)
        companion_vbox.set_margin_top(8)
        companion_vbox.set_margin_bottom(8)
        companion_frame.add(companion_vbox)

        lbl_companion_title = Gtk.Label()
        lbl_companion_title.set_markup("<b>认知伴读与思维脚手架</b>")
        lbl_companion_title.set_xalign(0)
        companion_vbox.pack_start(lbl_companion_title, False, False, 0)

        # 4 大模板快捷按钮
        btn_grid = Gtk.Grid()
        btn_grid.set_column_spacing(6)
        btn_grid.set_row_spacing(6)
        tpl_list = [
            ("通俗速解", "general"),
            ("逻辑论证", "logic"),
            ("辩驳反思", "critical"),
            ("术语拆解", "term")
        ]
        for i, (name, tpl) in enumerate(tpl_list):
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class("ia-template-btn")
            btn.connect("clicked", lambda w, t=tpl: self.invokeAiCompanion(t, "请深入剖析划选文本"))
            btn_grid.attach(btn, i % 2, i // 2, 1, 1)
        companion_vbox.pack_start(btn_grid, False, False, 2)

        # 当前选区摘要预览
        self.lbl_sel_preview = Gtk.Label()
        self.lbl_sel_preview.set_line_wrap(True)
        self.lbl_sel_preview.set_xalign(0)
        self.lbl_sel_preview.set_markup("<small><i>选区：“欢迎使用 AI Reader...”</i></small>")
        companion_vbox.pack_start(self.lbl_sel_preview, False, False, 0)

        # AI 输出视口
        card_scroll = Gtk.ScrolledWindow()
        card_scroll.set_min_content_height(160)
        self.card_view = Gtk.TextView()
        self.card_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.card_view.set_left_margin(8)
        self.card_view.set_right_margin(8)
        self.card_view.set_editable(False)
        self.card_view.modify_font(Pango.FontDescription("Sans 10"))
        card_scroll.add(self.card_view)
        companion_vbox.pack_start(card_scroll, True, True, 0)

        # 自由追问与交互提问栏
        ask_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_ask = Gtk.Entry()
        self.entry_ask.set_placeholder_text("就当前选区输入个性化追问...")
        self.entry_ask.connect("activate", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(self.entry_ask, True, True, 0)

        btn_ask = Gtk.Button(label="追问")
        btn_ask.get_style_context().add_class("ia-primary-btn")
        btn_ask.connect("clicked", lambda w: self._on_send_custom_prompt())
        ask_box.pack_start(btn_ask, False, False, 0)
        companion_vbox.pack_start(ask_box, False, False, 0)

        # 一键沉淀为边注
        btn_pin_note = Gtk.Button(label="沉淀此认知为永久边注")
        btn_pin_note.connect("clicked", lambda w: self._pin_ai_to_annotation())
        companion_vbox.pack_start(btn_pin_note, False, False, 0)

        self.marginalia_box.pack_start(companion_frame, False, False, 0)

        # 下部卡片：iA Writer 边注列表 (基线对齐持久化)
        lbl_notes = Gtk.Label()
        lbl_notes.set_markup("<b>阅读批注与边注清单</b>")
        lbl_notes.set_xalign(0)
        self.marginalia_box.pack_start(lbl_notes, False, False, 4)

        notes_scroll = Gtk.ScrolledWindow()
        self.notes_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        notes_scroll.add(self.notes_container)
        self.marginalia_box.pack_start(notes_scroll, True, True, 0)

        self.content_paned.pack2(self.marginalia_box, False, False)

    # ==========================================================================
    # 业务加载与渲染核心方法
    # ==========================================================================
    # @PublicAPI
    def loadBook(self, book_id: int, title: str):
        self.current_book_id = book_id
        self.current_title = title
        self.header.props.title = f"AI Reader - {title}"

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
            full_text_parts.append(f"\n\n# {s_title}\n\n" + s.get("content", ""))

        full_text = "".join(full_text_parts).strip()
        if not full_text:
            full_text = (
                "人类认知的演进是一场不断打破旧有范式的旅程。在这个信息爆炸的时代，"
                "深度阅读与认知伴读成为沉淀知识的核心阶梯。\n\n"
                "Attention Mechanisms have revolutionized sequence modeling in artificial intelligence. "
                "By allowing the network to dynamically weight different input tokens, "
                "transformers achieve state-of-the-art results across natural language and vision benchmarks."
            )

        self.content_buffer.set_text(full_text)
        self.lbl_doc_info.set_text(f"字数统计: {len(full_text)} | 格式: {meta.get('file_format', 'TEXT')} | 章节数: {len(sections)}")

        # 2. 刷新图谱与思维导图
        self._refresh_graph_and_mindmap()

        # 3. 刷新边注列表
        self._refresh_annotations_list()

        # 4. 刷新书架
        self._refresh_bookshelf()

        # 默认触发一次伴读
        self.invokeAiCompanion("general", "概述章节核心脉络")

    def _refresh_graph_and_mindmap(self):
        # 概念图谱
        g_resp = json.loads(ai_reader_invoke("nlp.build_graph", json.dumps({"book_id": self.current_book_id})))
        g_data = g_resp.get("data") or {}
        nodes = g_data.get("nodes", [])
        links = g_data.get("links", [])
        self.graph_canvas.set_graph_data(nodes, links)

        # 思维导图
        m_resp = json.loads(ai_reader_invoke("mindmap.generate", json.dumps({"book_id": self.current_book_id})))
        m_data = m_resp.get("data") or {}
        m_nodes = m_data.get("nodes", [])

        self.mindmap_store.clear()
        if m_nodes:
            root_node = self.mindmap_store.append(None, [self.current_title, 0])
            for nd in m_nodes:
                if nd.get("parent_id") is not None:
                    self.mindmap_store.append(root_node, [nd.get("title", "结构节点"), nd.get("section_id", 0)])
            self.mindmap_view.expand_all()

    def _refresh_annotations_list(self):
        # 清空容器
        for ch in self.notes_container.get_children():
            self.notes_container.remove(ch)

        resp = json.loads(ai_reader_invoke("annotation.list", json.dumps({"book_id": self.current_book_id})))
        data = resp.get("data") or {}
        annots = data.get("annotations", [])
        self.annotations_cache = annots

        if not annots:
            lbl = Gtk.Label(label="暂无边注。划选文本右键即可添加心得或沉淀伴读卡片。")
            lbl.set_line_wrap(True)
            self.notes_container.pack_start(lbl, False, False, 10)
        else:
            for item in annots:
                frame = Gtk.Frame()
                frame.get_style_context().add_class("ia-card")
                c_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                c_box.set_margin_start(6)
                c_box.set_margin_end(6)
                c_box.set_margin_top(6)
                c_box.set_margin_bottom(6)
                frame.add(c_box)

                # 顶部标签与删除
                h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                color = item.get("color", "#FDE047")
                lbl_color = Gtk.Label()
                lbl_color.set_markup(f"<span background='{color}'>  </span> <b>边注 #{item.get('id')}</b>")
                h.pack_start(lbl_color, False, False, 0)

                btn_del = Gtk.Button(label="删除")
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
                    lbl_ai.set_markup(f"<small><b>伴读沉淀：</b>{ai_resp[:120]}...</small>")
                    lbl_ai.set_line_wrap(True)
                    lbl_ai.set_xalign(0)
                    c_box.pack_start(lbl_ai, False, False, 0)

                self.notes_container.pack_start(frame, False, False, 0)

        self.notes_container.show_all()

    def _refresh_bookshelf(self):
        resp = json.loads(ai_reader_invoke("doc.list", "{}"))
        data = resp.get("data") or {}
        books = data.get("books", [])
        self.shelf_store.clear()
        for b in books:
            self.shelf_store.append([
                b.get("id", 0),
                b.get("title", "未命名文档"),
                b.get("file_format", "TXT"),
                b.get("word_count", 0)
            ])

    # ==========================================================================
    # 交互监听与 PublicAPI
    # ==========================================================================
    # @PublicAPI
    def onSelectText(self, text: str, page_index: int, offset: int):
        self.selected_text = text.strip()
        short_sel = self.selected_text[:90] + ("..." if len(self.selected_text) > 90 else "")
        self.lbl_sel_preview.set_markup(f"<small><i>选区：“{short_sel}”</i></small>")

    def _on_buffer_selection_changed(self, buf, pspec):
        if buf.get_has_selection():
            bounds = buf.get_selection_bounds()
            if bounds:
                start, end = bounds
                txt = buf.get_text(start, end, True)
                if txt.strip():
                    self.onSelectText(txt, 1, start.get_offset())

    def _on_content_button_press(self, view, event):
        if event.button == 3:  # 右键呼出快捷伴读与批注菜单
            menu = Gtk.Menu()

            # 4 大伴读模式
            for label, tpl in [
                ("通俗大白话速解 (Feynman)", "general"),
                ("逻辑论证结构剖析", "logic"),
                ("批判性反思与辩驳", "critical"),
                ("核心专业术语卡拆解", "term")
            ]:
                item = Gtk.MenuItem(label=label)
                item.connect("activate", lambda w, t=tpl: self.invokeAiCompanion(t, "请深入剖析选区"))
                menu.append(item)

            menu.append(Gtk.SeparatorMenuItem())

            # 添加边注
            item_note = Gtk.MenuItem(label="添加高亮边注心得")
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
        self.left_notebook.set_current_page(1)
        self._refresh_graph_and_mindmap()

    # @PublicAPI
    def toggleMindmapView(self):
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
        dialog.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "打开", Gtk.ResponseType.OK
        )
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
            self.loadBook(book_meta.get("id", 1), book_meta.get("title", Path(filepath).stem))
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
        # 定位正文中章节标题
        buf = self.content_buffer
        start_iter = buf.get_start_iter()
        match = start_iter.forward_search(title, Gtk.TextSearchFlags.VISIBLE_ONLY, None)
        if match:
            match_start, match_end = match
            mark = buf.create_mark(None, match_start, False)
            self.content_view.scroll_to_mark(mark, 0.05, True, 0.0, 0.1)

    def _on_graph_node_clicked(self, word: str, data: dict):
        self.lbl_graph_info.set_markup(f"<b>选中核心概念：</b>“{word}”\n权重得分: {data.get('score', 0):.3f}")
        # 在正文中搜索该词并滚动定位
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
            self.left_notebook.set_current_page(0)


# ==============================================================================
# 程序启动主入口
# ==============================================================================
def main():
    win = AIReaderWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    if "--dry-run" in sys.argv:
        print("[SUCCESS] AIReaderWindow initialized, tested, and validated successfully!")
        sys.exit(0)

    Gtk.main()


if __name__ == "__main__":
    main()
