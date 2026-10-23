#!/usr/bin/env python3
"""
跨项目全局偏好 / 技术学习笔记索引（Windows / Linux / macOS）。

权威源：Path.home()/.hs-dev-skill/preferences.yaml 与 tech_learning/*.md
查询缓存：同目录 global_index.sqlite（可重建）

每条笔记/偏好一条记录；标签（显式 + 同义词展开）用于加速检索。
仅依赖标准库 sqlite3 + pathlib；可选 PyYAML，缺失时用简易解析。
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from hs_paths import (
    ensure_utf8_stdout,
    global_root,
    preferences_path,
    tech_learning_dir,
)

DB_FILE_NAME = "global_index.sqlite"
SYNONYMS_FILE = "tag_synonyms.yaml"
SUMMARY_MAX = 480
BODY_MAX = 12000
DEFAULT_LIMIT = 8


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _norm_tag(tag: str) -> str:
    t = (tag or "").strip().strip("`").strip('"').strip("'")
    if not t:
        return ""
    # ASCII 小写；中文保持原样
    if re.fullmatch(r"[A-Za-z0-9_\.\-/+]+", t):
        return t.lower()
    return t


def _split_tags(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        text = str(raw)
        items = re.split(r"[,，;；|/、\s]+", text)
    out: List[str] = []
    seen: Set[str] = set()
    for it in items:
        n = _norm_tag(str(it))
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""


def _extract_summary(text: str, title: str = "") -> str:
    if not text:
        return (title or "")[:SUMMARY_MAX]
    lines: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("```") or s.startswith("---"):
            continue
        if s.startswith("#"):
            lines.append(s.lstrip("#").strip())
            continue
        lines.append(s)
        if sum(len(x) for x in lines) >= SUMMARY_MAX:
            break
    summary = " ".join(lines).strip() or (title or text[:SUMMARY_MAX])
    return summary[:SUMMARY_MAX]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    text = _read_text(path)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return _simple_yaml_load(text)


def _simple_yaml_load(text: str) -> Dict[str, Any]:
    """无 PyYAML 时的最小解析：preferences 列表项与 synonyms 映射。"""
    data: Dict[str, Any] = {"preferences": [], "synonyms": {}}
    # preferences blocks
    blocks = re.split(r"\n\s*-\s+category:\s*", text)
    for block in blocks[1:]:
        m_cat = re.match(r'"?([^"\n]+)"?', block.strip())
        if not m_cat:
            continue
        item: Dict[str, Any] = {"category": m_cat.group(1).strip()}
        for key in ("preference", "rationale", "source", "updated_at"):
            m = re.search(rf"{key}:\s*\"([^\"]*)\"|{key}:\s*(.+)", block)
            if m:
                item[key] = (m.group(1) if m.group(1) is not None else m.group(2) or "").strip()
        m_tags = re.search(r"tags:\s*\[([^\]]*)\]", block)
        if m_tags:
            item["tags"] = _split_tags(m_tags.group(1))
        data["preferences"].append(item)

    # synonyms: slug:\n    - tag
    syn: Dict[str, List[str]] = {}
    current: Optional[str] = None
    in_syn = False
    for line in text.splitlines():
        if re.match(r"^\s*synonyms:\s*$", line):
            in_syn = True
            continue
        if not in_syn:
            continue
        m_key = re.match(r"^\s{2,}([A-Za-z0-9_\-]+):\s*$", line)
        if m_key:
            current = m_key.group(1)
            syn.setdefault(current, [])
            continue
        m_tag = re.match(r"^\s+-\s+(.+)$", line)
        if m_tag and current:
            syn[current].append(m_tag.group(1).strip().strip('"').strip("'"))
    if syn:
        data["synonyms"] = syn
    return data


def _slug_from_note_name(name: str) -> str:
    base = Path(name).stem
    base = re.sub(r"_notes$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"_learning$", "", base, flags=re.IGNORECASE)
    return base.strip().lower() or base


def _explicit_tags_from_note(text: str) -> List[str]:
    tags: List[str] = []
    # YAML frontmatter
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if fm:
        m = re.search(r"(?mi)^tags:\s*\[([^\]]*)\]", fm.group(1))
        if m:
            tags.extend(_split_tags(m.group(1)))
        m2 = re.search(r"(?mi)^tags:\s*$([\s\S]*?)(?=^[a-zA-Z_]|\Z)", fm.group(1))
        if m2:
            for line in m2.group(1).splitlines():
                mm = re.match(r"^\s*-\s+(.+)$", line)
                if mm:
                    tags.extend(_split_tags(mm.group(1)))
    # 中文/Markdown 元数据行
    for pat in (
        r"(?mi)^-\s*\*\*标签\*\*[：:]\s*(.+)$",
        r"(?mi)^-\s*\*\*Tags?\*\*[：:]\s*(.+)$",
        r"(?mi)^标签[：:]\s*(.+)$",
        r"(?mi)^Tags?[：:]\s*(.+)$",
    ):
        m = re.search(pat, text)
        if m:
            tags.extend(_split_tags(m.group(1)))
    return _split_tags(tags)


class GlobalIndexDB:
    def __init__(self, global_dir: Optional[str | Path] = None):
        self.root = Path(global_dir).resolve() if global_dir else global_root().resolve()
        self.db_path = self.root / DB_FILE_NAME
        self.synonyms_path = self.root / SYNONYMS_FILE
        self.fts_available = False
        self._conn: Optional[sqlite3.Connection] = None
        self._synonyms: Dict[str, List[str]] = {}

    def connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self.root.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
        except sqlite3.Error:
            pass
        self._conn = conn
        self._ensure_schema(conn)
        return conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entries (
                entry_key TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                title TEXT,
                slug TEXT,
                path TEXT,
                tags TEXT,
                summary TEXT,
                body TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS entry_tags (
                tag TEXT NOT NULL,
                entry_key TEXT NOT NULL,
                PRIMARY KEY (tag, entry_key)
            );
            CREATE INDEX IF NOT EXISTS idx_entry_tags_tag ON entry_tags(tag);
            CREATE INDEX IF NOT EXISTS idx_entries_kind ON entries(kind);
            CREATE INDEX IF NOT EXISTS idx_entries_slug ON entries(slug);
            """
        )
        self.fts_available = self._try_init_fts(conn)
        conn.commit()

    def _try_init_fts(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                    entry_key UNINDEXED,
                    title,
                    slug,
                    tags,
                    summary,
                    body,
                    tokenize='unicode61'
                )
                """
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    def _load_synonyms(self) -> Dict[str, List[str]]:
        data = _load_yaml(self.synonyms_path)
        raw = data.get("synonyms") or {}
        out: Dict[str, List[str]] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                slug = _norm_tag(str(k))
                out[slug] = _split_tags(v)
        # 反向：任意标签也可映射回 slug 的标签集（检索扩展用）
        self._synonyms = out
        return out

    def expand_tags(self, tags: Iterable[str], *, slug: str = "") -> List[str]:
        syn = self._synonyms or self._load_synonyms()
        bag: List[str] = []
        seen: Set[str] = set()

        def add(t: str) -> None:
            n = _norm_tag(t)
            if n and n not in seen:
                seen.add(n)
                bag.append(n)

        for t in tags:
            add(t)
        if slug:
            add(slug)
            for t in syn.get(_norm_tag(slug), []):
                add(t)
        # 若显式标签命中某同义词表的值，并入该组
        for group_slug, group_tags in syn.items():
            group_set = set(group_tags) | {group_slug}
            if seen & group_set:
                add(group_slug)
                for t in group_tags:
                    add(t)
        return bag

    def extract_feature_tags(self, text: str, *, title: str = "", slug: str = "") -> List[str]:
        """
        从标题/正文提取特性标签：命中 tag_synonyms 中的 slug 或任一标签词则展开整组。
        例：正文出现「反向代理」→ 联想到 nginx 组（后端/WEB服务器/…）。
        """
        syn = self._synonyms or self._load_synonyms()
        hay = f"{title}\n{slug}\n{text}"
        hay_lower = hay.lower()
        found: List[str] = []

        for group_slug, group_tags in syn.items():
            needles = [group_slug] + list(group_tags)
            for needle in needles:
                n = _norm_tag(needle)
                if not n:
                    continue
                if re.fullmatch(r"[A-Za-z0-9_\.\-/+]+", n):
                    # ASCII：词边界近似
                    if re.search(rf"(?i)(?<![A-Za-z0-9_]){re.escape(n)}(?![A-Za-z0-9_])", hay):
                        found.append(group_slug)
                        found.extend(group_tags)
                        break
                else:
                    if n in hay or n.lower() in hay_lower:
                        found.append(group_slug)
                        found.extend(group_tags)
                        break

        return self.expand_tags(found, slug=slug)

    def rebuild(self) -> Dict[str, Any]:
        self._load_synonyms()
        conn = self.connect()
        conn.execute("DELETE FROM entries")
        conn.execute("DELETE FROM entry_tags")
        if self.fts_available:
            try:
                conn.execute("DELETE FROM entries_fts")
            except sqlite3.Error:
                self.fts_available = False

        count = 0
        for row in self._iter_notes():
            self._upsert(conn, row)
            count += 1
        for row in self._iter_preferences():
            self._upsert(conn, row)
            count += 1

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("rebuilt_at", _utc_now()),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("fts", "1" if self.fts_available else "0"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("root", str(self.root)),
        )
        conn.commit()
        payload = {
            "ok": True,
            "db_path": str(self.db_path),
            "global_root": str(self.root),
            "inserted": count,
            "fts": self.fts_available,
            "synonyms_loaded": len(self._synonyms),
            "rebuilt_at": _utc_now(),
        }
        self.close()
        return payload

    def _iter_notes(self) -> Iterable[Dict[str, Any]]:
        notes_dir = self.root / "tech_learning"
        if not notes_dir.is_dir():
            return
        for path in sorted(notes_dir.glob("*.md")):
            if path.name.startswith("_TEMPLATE"):
                continue
            text = _read_text(path)
            slug = _slug_from_note_name(path.name)
            title_m = re.search(r"(?m)^#\s+(.+)$", text)
            title = (title_m.group(1).strip() if title_m else path.stem)
            explicit = _explicit_tags_from_note(text)
            # 显式标签 + slug 同义词 + 正文特性抽取（如「反向代理」→ Nginx 组）
            auto = self.extract_feature_tags(text, title=title, slug=slug)
            tags = self.expand_tags(list(explicit) + list(auto), slug=slug)
            rel = f"tech_learning/{path.name}"
            yield {
                "entry_key": f"note:{slug}",
                "kind": "note",
                "title": title,
                "slug": slug,
                "path": rel,
                "tags": tags,
                "summary": _extract_summary(text, title),
                "body": text[:BODY_MAX],
                "updated_at": _utc_now(),
            }

    def _iter_preferences(self) -> Iterable[Dict[str, Any]]:
        pref_path = self.root / "preferences.yaml"
        data = _load_yaml(pref_path)
        prefs = data.get("preferences") or []
        if not isinstance(prefs, list):
            return
        for item in prefs:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category") or "").strip()
            if not category:
                continue
            tags = self.expand_tags(item.get("tags") or [], slug=category.split(".")[0])
            # category 段也作为标签
            for part in category.split("."):
                tags = self.expand_tags(tags + [part])
            preference = str(item.get("preference") or "")
            body = "\n".join(
                [
                    f"category: {category}",
                    f"preference: {preference}",
                    f"rationale: {item.get('rationale') or ''}",
                    f"source: {item.get('source') or ''}",
                    f"tags: {', '.join(tags)}",
                ]
            )
            yield {
                "entry_key": f"pref:{category}",
                "kind": "preference",
                "title": category,
                "slug": category.replace(".", "_"),
                "path": "preferences.yaml",
                "tags": tags,
                "summary": (preference or category)[:SUMMARY_MAX],
                "body": body[:BODY_MAX],
                "updated_at": str(item.get("updated_at") or _utc_now()),
            }

    def _upsert(self, conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
        tags: List[str] = list(row.get("tags") or [])
        tags_text = ", ".join(tags)
        conn.execute(
            """
            INSERT OR REPLACE INTO entries(
                entry_key, kind, title, slug, path, tags, summary, body, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["entry_key"],
                row["kind"],
                row.get("title") or "",
                row.get("slug") or "",
                row.get("path") or "",
                tags_text,
                row.get("summary") or "",
                row.get("body") or "",
                row.get("updated_at") or _utc_now(),
            ),
        )
        conn.execute("DELETE FROM entry_tags WHERE entry_key = ?", (row["entry_key"],))
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO entry_tags(tag, entry_key) VALUES (?, ?)",
                (tag, row["entry_key"]),
            )
        if self.fts_available:
            try:
                conn.execute("DELETE FROM entries_fts WHERE entry_key = ?", (row["entry_key"],))
                conn.execute(
                    """
                    INSERT INTO entries_fts(entry_key, title, slug, tags, summary, body)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["entry_key"],
                        row.get("title") or "",
                        row.get("slug") or "",
                        tags_text,
                        row.get("summary") or "",
                        row.get("body") or "",
                    ),
                )
            except sqlite3.Error:
                self.fts_available = False

    def search(
        self,
        query: str = "",
        *,
        tag: str = "",
        kind: str = "",
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        conn = self.connect()
        self._load_synonyms()
        q = (query or "").strip()
        tag_n = _norm_tag(tag)
        ranked: Dict[str, Dict[str, Any]] = {}

        # 标签精确/同义扩展
        tag_candidates: List[str] = []
        if tag_n:
            tag_candidates = self.expand_tags([tag_n])
        elif q:
            # 查询词本身也当标签试探
            tag_candidates = self.expand_tags([q]) if (len(q) <= 32) else []

        if tag_candidates:
            placeholders = ",".join("?" * len(tag_candidates))
            sql = f"""
                SELECT e.*, 0.0 AS score
                FROM entry_tags t
                JOIN entries e ON e.entry_key = t.entry_key
                WHERE t.tag IN ({placeholders})
            """
            params: List[Any] = list(tag_candidates)
            if kind:
                sql += " AND e.kind = ?"
                params.append(kind)
            for r in conn.execute(sql, params):
                ranked[r["entry_key"]] = self._row_to_result(r, source="tag")

        if q:
            use_fts = self.fts_available and not _has_cjk(q)
            if use_fts:
                fts_q = self._fts_query(q)
                try:
                    sql = """
                        SELECT e.*, bm25(entries_fts) AS score
                        FROM entries_fts
                        JOIN entries e ON e.entry_key = entries_fts.entry_key
                        WHERE entries_fts MATCH ?
                    """
                    params = [fts_q]
                    if kind:
                        sql += " AND e.kind = ?"
                        params.append(kind)
                    sql += " ORDER BY score LIMIT ?"
                    params.append(limit * 3)
                    for r in conn.execute(sql, params):
                        if r["entry_key"] not in ranked:
                            ranked[r["entry_key"]] = self._row_to_result(r, source="fts")
                except sqlite3.Error:
                    use_fts = False

            like = f"%{q}%"
            sql = """
                SELECT *, 0.0 AS score FROM entries
                WHERE (title LIKE ? OR slug LIKE ? OR tags LIKE ?
                       OR summary LIKE ? OR body LIKE ? OR entry_key LIKE ?)
            """
            params = [like, like, like, like, like, like]
            if kind:
                sql += " AND kind = ?"
                params.append(kind)
            sql += " LIMIT ?"
            params.append(limit * 3)
            for r in conn.execute(sql, params):
                if r["entry_key"] not in ranked:
                    ranked[r["entry_key"]] = self._row_to_result(r, source="like")

        if not q and not tag_n:
            return {
                "ok": False,
                "error": "empty query and tag",
                "results": [],
                "hint": "Use --q and/or --tag (e.g. --tag 反向代理).",
            }

        def _rank_key(item: Dict[str, Any]) -> Tuple[int, int, str]:
            src = {"tag": 0, "fts": 1, "like": 2}.get(item.get("source") or "", 3)
            kind_pen = 0 if item.get("kind") == "note" else 1
            return (src, kind_pen, item.get("entry_key") or "")

        results = sorted(ranked.values(), key=_rank_key)[:limit]
        return {
            "ok": True,
            "query": q or None,
            "tag": tag_n or None,
            "tag_expanded": tag_candidates or None,
            "kind": kind or None,
            "count": len(results),
            "results": results,
            "global_root": str(self.root),
            "hint": (
                "Token budget: open ONLY matched note/preference paths. "
                "Do not load entire tech_learning/ tree."
            ),
        }

    def _fts_query(self, q: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9_\.\-]+", q)
        if not tokens:
            return '"' + q.replace('"', " ") + '"'
        return " OR ".join(f'"{t}"' for t in tokens)

    def _row_to_result(self, row: sqlite3.Row, source: str) -> Dict[str, Any]:
        tags = _split_tags(row["tags"])
        return {
            "entry_key": row["entry_key"],
            "kind": row["kind"],
            "title": row["title"],
            "slug": row["slug"],
            "path": row["path"],
            "tags": tags,
            "summary": row["summary"],
            "source": source,
            "abs_path": str((self.root / row["path"]).resolve()) if row["path"] else None,
        }

    def tags(self, *, limit: int = 100) -> Dict[str, Any]:
        conn = self.connect()
        rows = conn.execute(
            """
            SELECT tag, COUNT(*) AS c
            FROM entry_tags
            GROUP BY tag
            ORDER BY c DESC, tag ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return {
            "ok": True,
            "count": len(rows),
            "tags": [{"tag": r["tag"], "entries": r["c"]} for r in rows],
            "global_root": str(self.root),
        }

    def get(self, key_or_path: str) -> Dict[str, Any]:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT * FROM entries
            WHERE entry_key = ? OR slug = ? OR path = ? OR title = ?
            LIMIT 1
            """,
            (key_or_path, key_or_path, key_or_path, key_or_path),
        ).fetchone()
        if not row:
            return {"ok": False, "error": f"not found: {key_or_path}", "result": None}
        return {
            "ok": True,
            "result": {
                **self._row_to_result(row, source="get"),
                "body_preview": (row["body"] or "")[:800],
            },
        }

    def stats(self) -> Dict[str, Any]:
        conn = self.connect()
        notes = conn.execute("SELECT COUNT(*) AS c FROM entries WHERE kind='note'").fetchone()["c"]
        prefs = conn.execute(
            "SELECT COUNT(*) AS c FROM entries WHERE kind='preference'"
        ).fetchone()["c"]
        tags = conn.execute("SELECT COUNT(DISTINCT tag) AS c FROM entry_tags").fetchone()["c"]
        meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
        return {
            "ok": True,
            "db_path": str(self.db_path),
            "global_root": str(self.root),
            "notes": notes,
            "preferences": prefs,
            "distinct_tags": tags,
            "fts": self.fts_available or meta.get("fts") == "1",
            "meta": meta,
        }


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ensure_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Index ~/.hs-dev-skill preferences & tech_learning (Win/Linux/macOS)"
    )
    parser.add_argument(
        "--global-root",
        default="",
        help="Override global root (default: Path.home()/.hs-dev-skill)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rebuild", help="Rebuild global SQLite index")
    sub.add_parser("stats", help="Show stats")
    sub.add_parser("tags", help="List tags with counts")

    p_search = sub.add_parser("search", help="Search by query and/or tag")
    p_search.add_argument("--q", default="", help="Free text / tech name")
    p_search.add_argument("--tag", default="", help="Tag e.g. 反向代理 / 后端")
    p_search.add_argument("--kind", default="", choices=["", "note", "preference"])
    p_search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    p_get = sub.add_parser("get", help="Get one entry by key/slug/path")
    p_get.add_argument("--key", required=True)

    p_suggest = sub.add_parser(
        "suggest-tags",
        help="Suggest feature tags for a note file (does not write)",
    )
    p_suggest.add_argument("--path", required=True, help="Path to *_notes.md")

    args = parser.parse_args(argv)
    db = GlobalIndexDB(args.global_root or None)
    try:
        if args.command == "rebuild":
            _print_json(db.rebuild())
            return 0
        if args.command == "stats":
            if not db.db_path.exists():
                db.rebuild()
                db = GlobalIndexDB(args.global_root or None)
            _print_json(db.stats())
            return 0
        if args.command == "tags":
            if not db.db_path.exists():
                db.rebuild()
                db = GlobalIndexDB(args.global_root or None)
            _print_json(db.tags())
            return 0
        if args.command == "search":
            if not db.db_path.exists():
                db.rebuild()
                db = GlobalIndexDB(args.global_root or None)
            _print_json(
                db.search(
                    args.q,
                    tag=args.tag,
                    kind=args.kind or "",
                    limit=args.limit,
                )
            )
            return 0
        if args.command == "get":
            if not db.db_path.exists():
                db.rebuild()
                db = GlobalIndexDB(args.global_root or None)
            _print_json(db.get(args.key))
            return 0
        if args.command == "suggest-tags":
            path = Path(args.path)
            if not path.is_file():
                # 相对全局 tech_learning
                alt = db.root / "tech_learning" / path.name
                path = alt if alt.is_file() else path
            if not path.is_file():
                _print_json({"ok": False, "error": f"file not found: {args.path}"})
                return 1
            text = _read_text(path)
            slug = _slug_from_note_name(path.name)
            title_m = re.search(r"(?m)^#\s+(.+)$", text)
            title = title_m.group(1).strip() if title_m else path.stem
            explicit = _explicit_tags_from_note(text)
            suggested = db.extract_feature_tags(text, title=title, slug=slug)
            merged = db.expand_tags(list(explicit) + list(suggested), slug=slug)
            _print_json(
                {
                    "ok": True,
                    "path": str(path),
                    "slug": slug,
                    "explicit_tags": explicit,
                    "suggested_tags": suggested,
                    "merged_tags": merged,
                    "hint": "Write merged_tags into note「标签」line, then rebuild.",
                }
            )
            return 0
    finally:
        db.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
