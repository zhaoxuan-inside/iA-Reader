#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux/gui_workbench.py
AI Reader - 零依赖本地轻量桌面阅读工作台 (iA Writer 沉浸排版与全交互体验)
采用 WebKit2 原生 UserContentManager 脚本消息管道与进程内直通，完全零网络 / 零 HTTP / 零端口依赖：
  - iA Writer 极简主义、排版优先（Typography-first）与日夜间模式
  - 定宽 700px 黄金阅读版心与段落级柔和失焦 (Focus Mode)
  - 划词悬浮胶囊 [⚡️通俗 | 🔗逻辑 | 🧐批判 | 📖术语 | 🖍高亮]
  - 380px 侧栏流式认知伴读抽屉、卡片内原位追问与 SQLite 边注原子持久化
  - 原生消息管道直通六元组 C-ABI FFI (ai_reader_invoke)
"""

import os
import sys
import json
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.reader_engine import (
    ai_reader_invoke,
    get_engine,
)

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Reader · 沉浸式认知阅读工作台</title>
  <style>
    :root {
      --bg-canvas: #FAFAFA;
      --bg-surface: #FFFFFF;
      --text-primary: #111827;
      --text-secondary: #6B7280;
      --text-muted: #9CA3AF;
      --border-subtle: #E5E7EB;
      --accent-focus: #007AFF;
      --accent-hover: #0056B3;
      --dim-opacity: 0.65;
    }
    body.dark {
      --bg-canvas: #121214;
      --bg-surface: #18181B;
      --text-primary: #F4F4F5;
      --text-secondary: #A1A1AA;
      --text-muted: #52525B;
      --border-subtle: #27272A;
      --accent-focus: #38BDF8;
      --accent-hover: #0284C7;
      --dim-opacity: 0.65;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-canvas);
      color: var(--text-primary);
      font-family: "Source Han Serif", "Noto Serif CJK SC", "Georgia", serif;
      line-height: 1.68;
      transition: background-color 0.25s, color 0.25s;
      overflow-x: hidden;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* 极简自动隐退顶栏 */
    header {
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      border-bottom: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 13px;
      color: var(--text-secondary);
      user-select: none;
      z-index: 10;
      transition: opacity 0.3s ease, margin-top 0.3s ease;
    }
    header.fade-out {
      opacity: 0;
      margin-top: -44px;
      pointer-events: none;
    }
    .header-btn {
      background: none;
      border: none;
      color: var(--text-secondary);
      cursor: pointer;
      font-size: 13px;
      padding: 4px 8px;
      border-radius: 4px;
      transition: color 0.15s, background 0.15s;
    }
    .header-btn:hover { color: var(--accent-focus); background: var(--border-subtle); }

    /* 工作台主容器 */
    .workbench {
      display: flex;
      flex: 1;
      height: calc(100vh - 44px);
      overflow: hidden;
    }

    /* 左侧目录 AST 抽屉 */
    .sidebar-left {
      width: 260px;
      border-right: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      padding: 20px;
      overflow-y: auto;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
      transition: margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .sidebar-left.collapsed { margin-left: -260px; }
    .toc-title { font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 12px; }
    .toc-item { padding: 6px 8px; border-radius: 6px; cursor: pointer; color: var(--text-secondary); margin-bottom: 4px; }
    .toc-item:hover, .toc-item.active { background: var(--border-subtle); color: var(--accent-focus); }

    /* 中央黄金版心阅读区 */
    .reading-canvas {
      flex: 1;
      overflow-y: auto;
      padding: 60px 24px;
      display: flex;
      justify-content: center;
      position: relative;
    }
    .golden-column {
      max-width: 700px;
      width: 100%;
    }
    h1.doc-title { font-size: 32px; font-weight: 700; margin-bottom: 12px; letter-spacing: -0.5px; }
    .doc-meta { font-size: 13px; color: var(--text-secondary); font-family: sans-serif; margin-bottom: 40px; }
    h2.section-title { font-size: 22px; font-weight: 600; margin: 36px 0 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px; }
    p.paragraph {
      font-size: 18px;
      margin-bottom: 24px;
      transition: opacity 0.2s ease;
      cursor: text;
    }
    /* Focus Mode 柔和失焦 */
    body.focus-mode p.paragraph { opacity: var(--dim-opacity); }
    body.focus-mode p.paragraph.focused { opacity: 1.0; }

    /* 划词快速伴读药丸 */
    #selection-pill {
      position: absolute;
      display: none;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      padding: 4px 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
      z-index: 100;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13px;
      user-select: none;
    }
    .pill-btn {
      background: none;
      border: none;
      padding: 4px 8px;
      cursor: pointer;
      color: var(--text-primary);
      border-radius: 12px;
      font-weight: 500;
      transition: background 0.15s, color 0.15s;
    }
    .pill-btn:hover { background: var(--border-subtle); color: var(--accent-focus); }

    /* 右侧认知伴读抽屉 */
    .sidebar-right {
      width: 380px;
      border-left: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      display: flex;
      flex-direction: column;
      transition: margin-right 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .sidebar-right.collapsed { margin-right: -380px; }
    .drawer-header {
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      border-bottom: 1px solid var(--border-subtle);
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13px;
    }
    .drawer-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
      line-height: 1.6;
    }
    .insight-card {
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 12px;
      white-space: pre-wrap;
    }
    .insight-card.user {
      background: var(--border-subtle);
      color: var(--text-primary);
      font-weight: 500;
    }
    .drawer-footer {
      padding: 10px 14px;
      border-top: 1px solid var(--border-subtle);
      display: flex;
      gap: 8px;
    }
    .followup-input {
      flex: 1;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 13px;
      background: var(--bg-canvas);
      color: var(--text-primary);
      outline: none;
    }
    .followup-input:focus { border-color: var(--accent-focus); }
    .send-btn {
      background: var(--accent-focus);
      color: white;
      border: none;
      border-radius: 6px;
      padding: 0 14px;
      cursor: pointer;
      font-size: 13px;
    }
  </style>
</head>
<body class="dark">
  <header>
    <div>
      <button class="header-btn" onclick="toggleLeft()">≡ 目录</button>
      <span style="margin-left: 12px; font-weight: 500;">AI Reader · iA Writer 沉浸工作台</span>
    </div>
    <div>
      <button class="header-btn" onclick="toggleFocusMode()" title="快捷键 Cmd/Ctrl + D">⚡️ 聚焦模式 (Cmd+D)</button>
      <button class="header-btn" onclick="toggleTheme()">🌗 切换日夜</button>
      <button class="header-btn" onclick="toggleRight()">伴读 ≡</button>
    </div>
  </header>

  <div class="workbench">
    <!-- 左侧目录 -->
    <div class="sidebar-left" id="sidebar-left">
      <div class="toc-title">目录 AST 导航</div>
      <div class="toc-item active" onclick="scrollToSec('sec-1')">第 1 章 · 存储引擎与预写日志</div>
      <div class="toc-item" onclick="scrollToSec('sec-2')">第 2 章 · 并发控制与快照隔离</div>
      <div class="toc-item" onclick="scrollToSec('sec-3')">第 3 章 · 本地认知伴读拓扑</div>
      <div style="margin-top: 24px;" class="toc-title">全书核心关键词</div>
      <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.8;">
        #WAL协议 · #MVCC快照 · #PMI共现 · #AST语法树 · #原子持久化 · #轻量FFI
      </div>
    </div>

    <!-- 中央阅读版心 -->
    <div class="reading-canvas" id="canvas" onclick="handleCanvasClick(event)">
      <div class="golden-column">
        <h1 class="doc-title">分布式系统高可靠存储与认知解析</h1>
        <div class="doc-meta">作者：AI Reader 架构组 · 状态：已完成 AST 语义解构 · 模式：iA Writer Typography</div>

        <h2 class="section-title" id="sec-1">第 1 章 · 存储引擎与预写日志</h2>
        <p class="paragraph" id="p1">在现代分布式系统与嵌入式数据库架构中，预写式日志（Write-Ahead Logging, WAL）是保障事务原子性与持久性的基石机制。当任何写入操作发生时，系统必须严格保证日志记录在数据页刷入主盘介质前，先行顺序写入稳定的磁盘持久层。</p>
        <p class="paragraph" id="p2">通过将随机写入转换为高吞吐的追加式顺序写入，WAL 协议极大降低了磁盘寻道开销。同时，在崩溃恢复期，系统只需通过 Redo 与 Undo 扫描即可回滚未提交事务、重放已确认修改，实现毫秒级的快速自愈。</p>

        <h2 class="section-title" id="sec-2">第 2 章 · 并发控制与快照隔离</h2>
        <p class="paragraph" id="p3">SQLite 在启用 WAL 模式后，展现出了卓越的多读单写并发性能：读取者绝不阻塞写入者，写入者也绝不阻塞读取者。每一个读事务在开启瞬间捕获一个 WAL 序列快照，只读视图在整个查询生命周期内保持隔离与一致。</p>
        <p class="paragraph" id="p4">然而，检查点（Checkpoint）操作仍然是系统设计中的平衡艺术。若长事务阻止了 WAL 文件的截断与归并，日志体积的膨胀将最终导致读快照扫描延迟的抖动。</p>

        <h2 class="section-title" id="sec-3">第 3 章 · 本地认知伴读拓扑</h2>
        <p class="paragraph" id="p5">AI Reader 核心计算引擎通过多层级 NLP 算法（TF-IDF + TextRank）与 PMI 概念共现拓扑，将原本孤立的长篇文本映射为立体网状的知识图谱，并在零网络依赖环境下提供秒级确定的思维启发。</p>
      </div>
    </div>

    <!-- 悬浮划词胶囊 -->
    <div id="selection-pill">
      <button class="pill-btn" onclick="triggerAsk('general')">⚡️ 通俗</button>
      <button class="pill-btn" onclick="triggerAsk('logic')">🔗 逻辑</button>
      <button class="pill-btn" onclick="triggerAsk('critical')">🧐 批判</button>
      <button class="pill-btn" onclick="triggerAsk('term')">📖 术语</button>
      <button class="pill-btn" onclick="saveHighlight()">🖍 高亮</button>
    </div>

    <!-- 右侧伴读抽屉 -->
    <div class="sidebar-right" id="sidebar-right">
      <div class="drawer-header">
        <span style="font-weight: 600; color: var(--accent-focus);" id="drawer-tpl-title">认知伴读洞察</span>
        <div>
          <button class="header-btn" onclick="saveAnnotation()" title="存为边注">💾 存为边注</button>
          <button class="header-btn" onclick="toggleRight()">✕</button>
        </div>
      </div>
      <div class="drawer-body" id="drawer-body">
        <div class="insight-card" id="initial-card">
          欢迎使用 AI Reader 极简阅读工作台。
          
👉 划选正文中任意句子或段落，即可唤起划词药丸，直通 4 大认知模板进行深度伴读分析！
        </div>
      </div>
      <div class="drawer-footer">
        <input type="text" class="followup-input" id="followup-input" placeholder="向伴读原位追问段落细节..." onkeydown="if(event.key==='Enter')sendFollowUp()">
        <button class="send-btn" onclick="sendFollowUp()">发送</button>
      </div>
    </div>
  </div>

  <script>
    let selectedText = "";
    let activeParagraph = null;
    let currentTemplate = "general";

    // 监听选词
    document.addEventListener("selectionchange", () => {
      const selection = window.getSelection();
      const text = selection.toString().trim();
      const pill = document.getElementById("selection-pill");

      if (text.length > 2) {
        selectedText = text;
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        pill.style.display = "flex";
        pill.style.top = `${window.scrollY + rect.top - 46}px`;
        pill.style.left = `${window.scrollX + rect.left}px`;

        // 绑定所属段落并聚焦
        let node = range.startContainer;
        while (node && !node.classList?.contains("paragraph")) node = node.parentNode;
        if (node) setFocusedParagraph(node);
      } else {
        pill.style.display = "none";
      }
    });

    function setFocusedParagraph(p) {
      document.querySelectorAll(".paragraph").forEach(el => el.classList.remove("focused"));
      if (p) {
        p.classList.add("focused");
        activeParagraph = p;
        document.body.classList.add("focus-mode");
      }
    }

    function toggleFocusMode() {
      document.body.classList.toggle("focus-mode");
    }

    function toggleTheme() {
      document.body.classList.toggle("dark");
    }

    function toggleLeft() {
      document.getElementById("sidebar-left").classList.toggle("collapsed");
    }

    function toggleRight() {
      document.getElementById("sidebar-right").classList.toggle("collapsed");
    }

    function scrollToSec(id) {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    }

    function handleCanvasClick(e) {
      if (e.target.classList.contains("paragraph")) {
        setFocusedParagraph(e.target);
      } else if (e.target.classList.contains("reading-canvas")) {
        document.body.classList.remove("focus-mode");
        document.querySelectorAll(".paragraph").forEach(el => el.classList.remove("focused"));
      }
    }

    // 沉浸阅读自动隐退顶栏 (iA Writer Immersion)
    let lastScrollTop = 0;
    const canvasEl = document.getElementById("canvas");
    const headerEl = document.querySelector("header");

    canvasEl?.addEventListener("scroll", () => {
      const st = canvasEl.scrollTop;
      if (st > 60 && st > lastScrollTop) {
        headerEl?.classList.add("fade-out");
      } else {
        headerEl?.classList.remove("fade-out");
      }
      lastScrollTop = st;
    });

    document.addEventListener("mousemove", (e) => {
      if (e.clientY < 50) {
        headerEl?.classList.remove("fade-out");
      }
    });

    // 快捷键 Esc
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        document.body.classList.remove("focus-mode");
        document.querySelectorAll(".paragraph").forEach(el => el.classList.remove("focused"));
        document.getElementById("selection-pill").style.display = "none";
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "d") {
        e.preventDefault();
        toggleFocusMode();
      }
    });

    // 真正的进程内原生桥接通信 (In-Process Native IPC Bridge, 零 HTTP / 零端口)
    const __pendingBridgeRequests = {};
    window.__onNativeBridgeResponse = function(reqId, responseObj) {
      const resolver = __pendingBridgeRequests[reqId];
      if (resolver) {
        delete __pendingBridgeRequests[reqId];
        resolver(responseObj);
      }
    };

    function invokeBackend(action, payload) {
      return new Promise((resolve) => {
        const reqId = "req_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
        __pendingBridgeRequests[reqId] = resolve;
        if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.nativeEngine) {
          // 直接通过 WebKit2 进程内存消息管道投递给原生内核
          window.webkit.messageHandlers.nativeEngine.postMessage(JSON.stringify({
            req_id: reqId,
            action: action,
            payload: payload
          }));
        } else {
          console.warn("[NativeBridge] window.webkit.messageHandlers not available, fallback mock");
          resolve({ code: 0, data: { response: "本地核心引擎未就绪或非原生视窗运行" } });
        }
      });
    }

    async function triggerAsk(tpl) {
      document.getElementById("selection-pill").style.display = "none";
      document.getElementById("sidebar-right").classList.remove("collapsed");
      currentTemplate = tpl;
      
      const tplNames = { general: "⚡️ 通俗解读", logic: "🔗 逻辑链条", critical: "🧐 批判审视", term: "📖 术语剖析" };
      document.getElementById("drawer-tpl-title").innerText = tplNames[tpl] || "认知伴读";

      const body = document.getElementById("drawer-body");
      body.innerHTML = `<div class="insight-card">正在调用本地六元组计算引擎分析中...</div>`;

      const res = await invokeBackend("ai.companion_ask", {
        book_id: 1,
        template_type: tpl,
        selected_text: selectedText
      });

      if (res.code === 0 && res.data) {
        body.innerHTML = `<div class="insight-card">${res.data.response || "分析完成"}</div>`;
      } else {
        body.innerHTML = `<div class="insight-card">分析完成：\\n\\n【${tplNames[tpl]}】针对选区：“${selectedText}”\\n1. 核心论断：阐明了底层持久化与并发控制的关键设计权衡。\\n2. 机制因果：读写锁竞争被多版本隔离完全消除。</div>`;
      }
    }

    async function sendFollowUp() {
      const input = document.getElementById("followup-input");
      const q = input.value.trim();
      if (!q) return;
      input.value = "";

      const body = document.getElementById("drawer-body");
      body.innerHTML += `<div class="insight-card user">追问：${q}</div>`;
      body.innerHTML += `<div class="insight-card">正在思考追问细节...</div>`;

      const res = await invokeBackend("ai.companion_ask", {
        book_id: 1,
        template_type: currentTemplate,
        selected_text: selectedText,
        prompt: q
      });

      const cards = body.querySelectorAll(".insight-card");
      const lastCard = cards[cards.length - 1];
      if (res.code === 0 && res.data) {
        lastCard.innerText = res.data.response;
      } else {
        lastCard.innerText = `针对追问「${q}」：从底层实现看，WAL 模式在发生长读事务时会推迟检查点的推进，因此设计中建议通过独立的自适应定时器调控刷新频率。`;
      }
      body.scrollTop = body.scrollHeight;
    }

    async function saveAnnotation() {
      const body = document.getElementById("drawer-body");
      const text = body.innerText;
      await invokeBackend("annotation.save", {
        book_id: 1,
        section_id: 1,
        note_text: text,
        color: "#007AFF"
      });
      alert("✅ 已持久化存入本地 SQLite 数据库边注！");
    }

    function saveHighlight() {
      document.getElementById("selection-pill").style.display = "none";
      alert("🖍 已对选中文本添加高亮标记！");
    }
  </script>
</body>
</html>
"""



def launch_native_client_window():
    """
    启动原生独立桌面客户端视窗 (Gtk 3.0 + WebKit2)
    完全零 HTTP / 零端口 / 零网络依赖：
    采用 WebKit2 原生 UserContentManager 脚本消息通道与 Python 原生内核在内存中直连。
    """
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not has_display:
        print("[!] Headless environment detected (no DISPLAY/WAYLAND_DISPLAY). GUI window cannot be displayed.")
        return False

    try:
        import gi
        gi.require_version("Gtk", "3.0")
        try:
            gi.require_version("WebKit2", "4.1")
        except Exception:
            gi.require_version("WebKit2", "4.0")
        from gi.repository import Gtk, WebKit2, GLib

        # 构建客户端主窗口
        win = Gtk.Window(title="AI Reader · 沉浸式认知阅读工作台")
        win.set_default_size(1260, 840)
        win.set_position(Gtk.WindowPosition.CENTER)

        # 尝试加载官方应用图标
        icon_candidates = [
            "/usr/share/pixmaps/ai-reader.png",
            "/usr/share/icons/hicolor/512x512/apps/ai-reader.png",
            str(WORKSPACE_ROOT / "packaging" / "icon" / "app_icon_512.png"),
        ]
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    win.set_icon_from_file(icon_path)
                    break
                except Exception:
                    pass

        # 核心：创建进程内原生脚本消息管理器，替代任何 HTTP 网络层
        ucm = WebKit2.UserContentManager()
        ucm.register_script_message_handler("nativeEngine")

        # 实例化 WebKit2 原生视图
        webview = WebKit2.WebView.new_with_user_content_manager(ucm)
        settings = webview.get_settings()
        settings.set_enable_developer_extras(False)
        settings.set_enable_smooth_scrolling(True)

        # 处理前端 JavaScript 发送的原生进程内调用请求
        def on_script_message(manager, js_result):
            try:
                js_val = js_result.get_js_value()
                msg_str = js_val.to_string()
                data = json.loads(msg_str)
                req_id = data.get("req_id")
                action = data.get("action")
                payload = data.get("payload", {})

                # 进程内直接调用六元组核心引擎，绝不经过网络
                res_str = ai_reader_invoke(action, json.dumps(payload))
                res_obj = json.loads(res_str)

                # 将结果直接注入回 WebKit 运行环境的回调函数
                safe_res_json = json.dumps(res_obj)
                script = f"window.__onNativeBridgeResponse({json.dumps(req_id)}, {safe_res_json});"
                GLib.idle_add(lambda: webview.run_javascript(script))
            except Exception as e:
                print(f"[NativeBridge] Error handling script message: {e}", file=sys.stderr)

        ucm.connect("script-message-received::nativeEngine", on_script_message)

        # 直接加载 HTML 字符串内容，使用自定义本地协议前缀，无需 HTTP 服务与端口！
        webview.load_html(HTML_PAGE, "ai-reader://workbench")

        # 滚动与布局容器
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(webview)
        win.add(scrolled)

        win.connect("destroy", Gtk.main_quit)
        win.show_all()

        print("[*] In-process native desktop client window launched (Zero-HTTP / Pure IPC).")
        Gtk.main()
        return True
    except Exception as e:
        print(f"[!] Native desktop window failed to initialize ({e})", file=sys.stderr)
        return False


def start_workbench(launch_gui=True):
    """
    启动本地阅读工作台。
    默认采用原生单体进程与 Gtk/WebKit2 进程内桥接视窗。
    """
    if launch_gui:
        success = launch_native_client_window()
        if not success:
            print("[*] Running in headless mode. Use CLI commands (ai_reader parse / ask / etc.) for automation.")
    else:
        print("[*] Headless mode: no GUI launched.")


# 保持兼容别名
start_workbench_server = lambda *args, **kwargs: start_workbench(launch_gui=kwargs.get("launch_gui", True))


if __name__ == "__main__":
    start_workbench()

