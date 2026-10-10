#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux/ai_reader_app.py
AI Reader - Headless Core Computation & Document Parsing Engine CLI
Pure CLI Interface: Zero GUI dependencies (no GTK, no X11/Wayland, no Flutter).
Provides command-line interfaces for:
  - doc.parse: Multi-format (Markdown, TXT, EPUB, PDF) parsing into AST
  - nlp.keyword_extract: Tri-level offline NLP keyword extraction (TF-IDF + TextRank)
  - graph.build: Co-occurrence topology graph generation (PMI)
  - mindmap.generate: AST knowledge tree & structured mindmap generation
  - ai.companion_ask: Cognitive companion stream & multi-template Q&A
  - annotation.*: SQLite persistent annotation management
  - invoke: Low-level six-tuple FFI dispatch protocol bridge
"""

import sys
import os
import json
import argparse
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if (APP_DIR / "backend").exists():
    WORKSPACE_ROOT = APP_DIR
else:
    WORKSPACE_ROOT = APP_DIR.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.reader_engine import (
    ai_reader_invoke,
    dispatch_invoke,
    get_engine,
    get_llm_config,
)


def format_json_output(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def handle_parse(args):
    file_path = str(Path(args.file).resolve())
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    payload = json.dumps({"file_path": file_path})
    res_raw = ai_reader_invoke("doc.parse", payload)
    res = json.loads(res_raw)
    
    if res.get("code") == 0:
        data = res.get("data", {})
        print(f"[SUCCESS] Document parsed successfully:")
        print(f"  Book ID:        {data.get('book_id')}")
        print(f"  Title:          {data.get('title')}")
        print(f"  Total Sections: {data.get('sections_count')}")
        print(f"  Duration:       {res.get('metrics', {}).get('duration_ms')}ms")
    else:
        print(f"[FAIL] Parse error: {res.get('message')}", file=sys.stderr)
        sys.exit(1)


def handle_books(args):
    res_raw = ai_reader_invoke("book.list", "{}")
    res = json.loads(res_raw)
    if res.get("code") == 0:
        books = res.get("data", {}).get("books", [])
        if not books:
            print("[INFO] No books in local library.")
            return
        print(f"{'ID':<6} {'Format':<8} {'Sections':<10} {'Title'}")
        print("-" * 60)
        for b in books:
            print(f"{b.get('id', ''):<6} {b.get('format', ''):<8} {b.get('total_pages', 0):<10} {b.get('title', '')}")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_book(args):
    payload = json.dumps({"book_id": args.book_id})
    res_raw = ai_reader_invoke("book.detail", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        data = res.get("data", {})
        book = data.get("book", {})
        sections = data.get("sections", [])
        print(f"Book #{book.get('id')}: {book.get('title')}")
        print(f"Author: {book.get('author')}, Format: {book.get('format')}, File: {book.get('file_path')}")
        print(f"Sections ({len(sections)}):")
        for s in sections[:args.limit]:
            print(f"  [{s.get('section_index')}] {s.get('title')}")
        if len(sections) > args.limit:
            print(f"  ... and {len(sections) - args.limit} more sections.")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_keywords(args):
    payload = json.dumps({"book_id": args.book_id, "top_k": args.top_k})
    res_raw = ai_reader_invoke("nlp.keyword_extract", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        keywords = res.get("data", {}).get("keywords", [])
        print(f"[SUCCESS] Top {len(keywords)} Keywords for Book #{args.book_id} (Duration: {res.get('metrics', {}).get('duration_ms')}ms):")
        print(f"{'Rank':<6} {'Keyword / Concept':<35} {'TF-IDF':<10} {'TextRank':<10}")
        print("-" * 65)
        for idx, kw in enumerate(keywords, 1):
            w_name = kw.get('word') or kw.get('keyword') or ''
            tf = kw.get('tfidf_score', kw.get('weight', 0.0))
            tr = kw.get('textrank_score', 0.0)
            print(f"{idx:<6} {w_name:<35} {tf:<10.4f} {tr:<10.4f}")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_graph(args):
    payload = json.dumps({"book_id": args.book_id, "window_size": args.window_size})
    res_raw = ai_reader_invoke("graph.build", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        data = res.get("data", {})
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        print(f"[SUCCESS] Concept Topology Graph for Book #{args.book_id}:")
        print(f"  Nodes: {len(nodes)}, Edges: {len(edges)}, Duration: {res.get('metrics', {}).get('duration_ms')}ms")
        if args.verbose:
            print("\nTop Edges (Co-occurrences):")
            for e in sorted(edges, key=lambda x: x.get('pmi_score', 0), reverse=True)[:args.limit]:
                print(f"  {e.get('source')} <--> {e.get('target')} (co_occur: {e.get('co_occurrence_count')}, PMI: {e.get('pmi_score', 0):.2f})")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_mindmap(args):
    payload = json.dumps({"book_id": args.book_id})
    res_raw = ai_reader_invoke("mindmap.generate", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        nodes = res.get("data", {}).get("nodes", [])
        print(f"[SUCCESS] Mindmap Generated for Book #{args.book_id} ({len(nodes)} nodes, Duration: {res.get('metrics', {}).get('duration_ms')}ms):")
        for n in nodes:
            indent = "  " * (n.get("level", 1) - 1)
            print(f"{indent}- {n.get('title')}")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_ask(args):
    payload = json.dumps({
        "book_id": args.book_id,
        "template_type": args.template,
        "selected_text": args.text or "",
        "prompt": args.prompt or ""
    })
    res_raw = ai_reader_invoke("ai.companion_ask", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        data = res.get("data", {})
        print(f"\n--- AI Cognitive Companion [{data.get('template_type')}] ---")
        print(data.get("response", ""))
        print("---------------------------------------------------")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_annotations(args):
    payload = json.dumps({"book_id": args.book_id})
    res_raw = ai_reader_invoke("annotation.list", payload)
    res = json.loads(res_raw)
    if res.get("code") == 0:
        annots = res.get("data", {}).get("annotations", [])
        print(f"[SUCCESS] Annotations for Book #{args.book_id} ({len(annots)} items):")
        for a in annots:
            print(f"  ID: {a.get('id')} | Style: {a.get('style')} | Color: {a.get('color')}")
            if a.get('note_text'):
                print(f"    Note: {a.get('note_text')}")
    else:
        print(f"[FAIL] Error: {res.get('message')}", file=sys.stderr)


def handle_invoke(args):
    res_raw = ai_reader_invoke(args.action, args.payload or "{}")
    if args.pretty:
        try:
            print(format_json_output(json.loads(res_raw)))
        except Exception:
            print(res_raw)
    else:
        print(res_raw)


def main():
    parser = argparse.ArgumentParser(
        prog="ai-reader",
        description="AI Reader - Headless Core Computation & Document Parsing Engine CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse document (MD/TXT/EPUB/PDF) into AST")
    p_parse.add_argument("file", help="Path to document file")

    # books
    subparsers.add_parser("books", help="List imported books in local storage")

    # book
    p_book = subparsers.add_parser("book", help="View book metadata and sections")
    p_book.add_argument("book_id", type=int, help="Book ID")
    p_book.add_argument("--limit", type=int, default=10, help="Max sections to display")

    # keywords
    p_kw = subparsers.add_parser("keywords", help="Extract keywords using offline NLP (TF-IDF + TextRank)")
    p_kw.add_argument("book_id", type=int, help="Book ID")
    p_kw.add_argument("--top-k", type=int, default=10, help="Number of top keywords (default: 10)")

    # graph
    p_graph = subparsers.add_parser("graph", help="Build PMI concept co-occurrence topology graph")
    p_graph.add_argument("book_id", type=int, help="Book ID")
    p_graph.add_argument("--window-size", type=int, default=5, help="Co-occurrence sliding window")
    p_graph.add_argument("--verbose", "-v", action="store_true", help="Show edges and PMI scores")
    p_graph.add_argument("--limit", type=int, default=15, help="Max edges to display")

    # mindmap
    p_map = subparsers.add_parser("mindmap", help="Generate structured mindmap AST tree")
    p_map.add_argument("book_id", type=int, help="Book ID")

    # ask
    p_ask = subparsers.add_parser("ask", help="Query AI cognitive companion")
    p_ask.add_argument("book_id", type=int, help="Book ID")
    p_ask.add_argument("--template", choices=["general", "plain", "logic", "critical", "terminology"], default="general")
    p_ask.add_argument("--text", default="", help="Context selected text")
    p_ask.add_argument("--prompt", default="", help="Custom question prompt")

    # annotations
    p_ann = subparsers.add_parser("annotations", help="List annotations for a book")
    p_ann.add_argument("book_id", type=int, help="Book ID")

    # invoke (low level)
    p_inv = subparsers.add_parser("invoke", help="Execute low-level six-tuple FFI action")
    p_inv.add_argument("--action", required=True, help="Action name (e.g., doc.parse, nlp.keyword_extract)")
    p_inv.add_argument("--payload", default="{}", help="JSON payload string")
    p_inv.add_argument("--pretty", action="store_true", help="Pretty-print JSON response")

    # workbench / gui
    p_wb = subparsers.add_parser("workbench", help="Launch interactive iA Writer native GUI reading workbench")
    p_wb.add_argument("--no-gui", action="store_true", help="Run in headless mode (do not launch GUI window)")

    def start_ui_workbench(launch_gui=True):
        if not launch_gui:
            print("[*] Headless mode: no GUI launched.")
            return
        # 优先拉起真正的 Flutter Linux 客户端 (Impeller / iA Writer 沉浸排版)
        candidates = [
            APP_DIR / "bundle/ai_reader",
            APP_DIR.parent / "frontend/build/linux/x64/release/bundle/ai_reader",
            Path("/usr/lib/ai-reader/bundle/ai_reader"),
        ]
        for c in candidates:
            if c.exists() and os.access(c, os.X_OK):
                print(f"[*] Launching Flutter Linux native client: {c}")
                try:
                    subprocess.run([str(c)])
                    return
                except Exception as e:
                    print(f"[!] Flutter client failed ({e}), falling back...", file=sys.stderr)
                    break
        try:
            from linux.gui_workbench import start_workbench
        except ImportError:
            from gui_workbench import start_workbench
        start_workbench(launch_gui=True)

    # 如果系统通过桌面直接传入单个已存在文档路径 (例如从文件管理器双击文件)
    if len(sys.argv) == 2 and os.path.exists(sys.argv[1]) and not sys.argv[1].startswith("-"):
        doc_path = str(Path(sys.argv[1]).resolve())
        print(f"[*] Opening document in AI Reader: {doc_path}")
        ai_reader_invoke("doc.parse", json.dumps({"file_path": doc_path}))
        start_ui_workbench(launch_gui=True)
        return

    args = parser.parse_args()
    if not args.command:
        # 桌面图标双击启动或无参数启动：自动拉起 Flutter 沉浸式原生客户端
        start_ui_workbench(launch_gui=True)
        return

    def handle_workbench(a):
        start_ui_workbench(launch_gui=not a.no_gui)

    handlers = {
        "parse": handle_parse,
        "books": handle_books,
        "book": handle_book,
        "keywords": handle_keywords,
        "graph": handle_graph,
        "mindmap": handle_mindmap,
        "ask": handle_ask,
        "annotations": handle_annotations,
        "invoke": handle_invoke,
        "workbench": handle_workbench,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
