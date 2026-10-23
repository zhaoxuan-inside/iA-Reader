#!/usr/bin/env python3
"""
领域规则库：本地高频 craft + GitHub 远程按需拉取（Windows / Linux / macOS）。

权威目录：<skill_root>/resources/rule_sources.yaml
缓存：Path.home()/.hs-dev-skill/rule_cache/（可重建）

设计目标：
- 禁止预拉全部远程包
- github_tree 必须 --rule 拉单条小文件
- 网络失败时返回可行动错误 + 本地/缓存回退提示
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from hs_paths import ensure_utf8_stdout, rule_cache_dir

DEFAULT_TTL_HOURS = 168
USER_AGENT = "hs-dev-skill-rule-fetch/1.0"
SLICE_DEFAULT = 40


def skill_root_from_here() -> Path:
    here = Path(__file__).resolve().parent
    candidate = here.parent
    if (candidate / "SKILL.md").is_file():
        return candidate
    for parent in here.parents:
        if (parent / "SKILL.md").is_file() and (parent / "references").is_dir():
            return parent
    return candidate


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""


def _split_tags(raw: str) -> List[str]:
    parts = re.split(r"[,，\s]+", raw.strip())
    return [p.strip().strip("\"'") for p in parts if p.strip().strip("\"'")]


def _parse_sources_yaml(text: str) -> Dict[str, Any]:
    """无 PyYAML 时解析本仓库 rule_sources.yaml 的受限子集。"""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if isinstance(data, dict) and isinstance(data.get("sources"), list):
            return data
    except Exception:
        pass

    policy: Dict[str, Any] = {}
    sources: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    in_sources = False
    in_policy = False

    for raw in text.splitlines():
        if re.match(r"^\s*#", raw) or not raw.strip():
            continue
        if re.match(r"^policy:\s*$", raw):
            in_policy = True
            in_sources = False
            continue
        if re.match(r"^sources:\s*$", raw):
            in_sources = True
            in_policy = False
            current = None
            continue
        if in_policy:
            m = re.match(r"^\s{2,}([A-Za-z0-9_]+):\s*(.+)\s*$", raw)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if re.fullmatch(r"\d+", val):
                    policy[key] = int(val)
                elif val.lower() in {"true", "false"}:
                    policy[key] = val.lower() == "true"
                else:
                    policy[key] = val.strip("\"'")
            continue
        if not in_sources:
            continue
        m_id = re.match(r"^\s*-\s+id:\s*(.+)\s*$", raw)
        if m_id:
            current = {"id": m_id.group(1).strip().strip("\"'")}
            sources.append(current)
            continue
        if current is None:
            continue
        m_list = re.match(r"^\s{2,}([A-Za-z0-9_]+):\s*\[([^\]]*)\]\s*$", raw)
        if m_list:
            current[m_list.group(1)] = _split_tags(m_list.group(2))
            continue
        m_kv = re.match(r"^\s{2,}([A-Za-z0-9_]+):\s*(.+)\s*$", raw)
        if m_kv:
            key, val = m_kv.group(1), m_kv.group(2).strip()
            current[key] = val.strip("\"'")
    return {"version": 1, "policy": policy, "sources": sources}


def load_catalog(skill_root: Path) -> Dict[str, Any]:
    path = skill_root / "resources" / "rule_sources.yaml"
    if not path.is_file():
        return {"version": 1, "policy": {}, "sources": [], "error": f"missing {path.as_posix()}"}
    data = _parse_sources_yaml(_read_text(path))
    data.setdefault("policy", {})
    data.setdefault("sources", [])
    data["catalog_path"] = path.as_posix()
    return data


def _source_by_id(catalog: Dict[str, Any], source_id: str) -> Optional[Dict[str, Any]]:
    for s in catalog.get("sources") or []:
        if isinstance(s, dict) and s.get("id") == source_id:
            return s
    return None


def _raw_urls(repo: str, ref: str, file_path: str) -> List[str]:
    file_path = file_path.lstrip("/")
    return [
        f"https://raw.githubusercontent.com/{repo}/{ref}/{file_path}",
        f"https://cdn.jsdelivr.net/gh/{repo}@{ref}/{file_path}",
    ]


def _http_get(url: str, timeout: float = 25.0) -> Tuple[bool, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            text = body.decode("utf-8", errors="replace")
            return True, text, ""
    except urllib.error.HTTPError as e:
        return False, "", f"HTTP {e.code} for {url}"
    except Exception as e:
        return False, "", f"{type(e).__name__}: {e} ({url})"


def _cache_paths(cache_root: Path, source_id: str, rule: Optional[str] = None) -> Tuple[Path, Path]:
    safe = re.sub(r"[^\w.\-]+", "_", source_id)
    if rule:
        safe_rule = re.sub(r"[^\w.\-]+", "_", rule)
        base = cache_root / safe / f"{safe_rule}.md"
        meta = cache_root / safe / f"{safe_rule}.meta.json"
    else:
        base = cache_root / f"{safe}.md"
        meta = cache_root / f"{safe}.meta.json"
    return base, meta


def _meta_fresh(meta_path: Path, ttl_hours: int) -> bool:
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(_read_text(meta_path) or "{}")
        fetched_at = float(meta.get("fetched_epoch") or 0)
        return (time.time() - fetched_at) < ttl_hours * 3600
    except Exception:
        return False


def _write_cache(body_path: Path, meta_path: Path, text: str, meta: Dict[str, Any]) -> None:
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_text(text, encoding="utf-8")
    meta = dict(meta)
    meta["fetched_at"] = _utc_now()
    meta["fetched_epoch"] = time.time()
    meta["bytes"] = len(text.encode("utf-8"))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _download(urls: Sequence[str]) -> Tuple[bool, str, str, str]:
    errors: List[str] = []
    for url in urls:
        ok, text, err = _http_get(url)
        if ok and text.strip():
            return True, text, url, ""
        errors.append(err or f"empty body: {url}")
    return False, "", "", " | ".join(errors)


def list_sources(catalog: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for s in catalog.get("sources") or []:
        if not isinstance(s, dict):
            continue
        rows.append(
            {
                "id": s.get("id"),
                "kind": s.get("kind"),
                "tags": s.get("tags") or [],
                "when": s.get("when") or "",
                "rule_examples": s.get("rule_examples") or [],
            }
        )
    return {"ok": True, "count": len(rows), "sources": rows, "policy": catalog.get("policy") or {}}


def search_catalog(catalog: Dict[str, Any], q: str, limit: int = 8) -> Dict[str, Any]:
    q_l = (q or "").strip().lower()
    hits: List[Dict[str, Any]] = []
    for s in catalog.get("sources") or []:
        if not isinstance(s, dict):
            continue
        blob = " ".join(
            [
                str(s.get("id") or ""),
                str(s.get("when") or ""),
                " ".join(s.get("tags") or []),
                " ".join(s.get("rule_examples") or []),
                str(s.get("file") or ""),
                str(s.get("base_path") or ""),
                str(s.get("file_template") or ""),
            ]
        ).lower()
        score = 0
        if not q_l:
            score = 1
        else:
            for token in re.split(r"\s+", q_l):
                if token and token in blob:
                    score += 2 if token in str(s.get("id") or "").lower() else 1
        if score <= 0:
            continue
        hits.append(
            {
                "score": score,
                "id": s.get("id"),
                "kind": s.get("kind"),
                "when": s.get("when") or "",
                "tags": s.get("tags") or [],
                "hint": (
                    f"resolve --id {s.get('id')} --rule <name>"
                    if s.get("kind") == "github_tree"
                    else f"resolve --id {s.get('id')}"
                ),
            }
        )
    hits.sort(key=lambda h: (-int(h["score"]), str(h["id"])))
    return {"ok": True, "q": q, "hits": hits[: max(1, limit)]}


def resolve_source(
    skill_root: Path,
    catalog: Dict[str, Any],
    source_id: str,
    rule: Optional[str] = None,
    force: bool = False,
    cache_root: Optional[Path] = None,
) -> Dict[str, Any]:
    src = _source_by_id(catalog, source_id)
    if not src:
        return {"ok": False, "error": f"unknown source id: {source_id}", "hint": "run list"}

    kind = (src.get("kind") or "").strip()
    ttl = int((catalog.get("policy") or {}).get("cache_ttl_hours") or DEFAULT_TTL_HOURS)
    cache_root = cache_root or rule_cache_dir()

    if kind == "local":
        rel = str(src.get("path") or "")
        path = (skill_root / rel).resolve()
        if not path.is_file():
            return {"ok": False, "error": f"local path missing: {rel}"}
        text = _read_text(path)
        return {
            "ok": True,
            "id": source_id,
            "kind": kind,
            "path": path.as_posix(),
            "cached": False,
            "bytes": len(text.encode("utf-8")),
            "preview": text[:400],
            "instruction": "Read this local craft file (already may be in session); do not also dump remote packs.",
        }

    if kind == "github_tree":
        if not rule:
            examples = src.get("rule_examples") or []
            return {
                "ok": False,
                "error": "github_tree requires --rule <filename-stem>",
                "rule_examples": examples,
                "hint": f"example: resolve --id {source_id} --rule {(examples[0] if examples else 'async-parallel')}",
            }
        rule_stem = rule[:-3] if rule.endswith(".md") else rule
        # file_template 支持嵌套路径，如 "{rule}/DESIGN.md"（awesome-design-md）
        template = str(src.get("file_template") or "{rule}.md").strip()
        if "{rule}" not in template:
            template = "{rule}.md"
        rel = template.replace("{rule}", rule_stem).lstrip("/")
        base = str(src.get("base_path") or "").rstrip("/")
        file_path = f"{base}/{rel}" if base else rel
        body, meta = _cache_paths(cache_root, source_id, rule_stem)
        if not force and body.is_file() and _meta_fresh(meta, ttl):
            text = _read_text(body)
            return {
                "ok": True,
                "id": source_id,
                "kind": kind,
                "rule": rule_stem,
                "path": body.as_posix(),
                "cached": True,
                "bytes": len(text.encode("utf-8")),
                "preview": text[:400],
            }
        urls = _raw_urls(str(src["repo"]), str(src.get("ref") or "main"), file_path)
        ok, text, used, err = _download(urls)
        if not ok:
            if body.is_file():
                stale = _read_text(body)
                return {
                    "ok": True,
                    "id": source_id,
                    "kind": kind,
                    "rule": rule_stem,
                    "path": body.as_posix(),
                    "cached": True,
                    "stale": True,
                    "fetch_error": err,
                    "bytes": len(stale.encode("utf-8")),
                    "preview": stale[:400],
                    "warning": "network failed; using stale cache",
                }
            return {
                "ok": False,
                "error": err,
                "urls_tried": urls,
                "fallback": "use local.frontend.core / WebFetch the first url, then save under rule_cache",
            }
        _write_cache(
            body,
            meta,
            text,
            {"id": source_id, "kind": kind, "rule": rule_stem, "url": used, "repo": src.get("repo")},
        )
        return {
            "ok": True,
            "id": source_id,
            "kind": kind,
            "rule": rule_stem,
            "path": body.as_posix(),
            "cached": False,
            "url": used,
            "bytes": len(text.encode("utf-8")),
            "preview": text[:400],
        }

    if kind == "github_raw":
        file_path = str(src.get("file") or "")
        body, meta = _cache_paths(cache_root, source_id)
        if not force and body.is_file() and _meta_fresh(meta, ttl):
            text = _read_text(body)
            return {
                "ok": True,
                "id": source_id,
                "kind": kind,
                "path": body.as_posix(),
                "cached": True,
                "bytes": len(text.encode("utf-8")),
                "preview": text[:400],
                "instruction": "Prefer search-cache before reading full file into context.",
            }
        urls = _raw_urls(str(src["repo"]), str(src.get("ref") or "main"), file_path)
        ok, text, used, err = _download(urls)
        if not ok:
            if body.is_file():
                stale = _read_text(body)
                return {
                    "ok": True,
                    "id": source_id,
                    "kind": kind,
                    "path": body.as_posix(),
                    "cached": True,
                    "stale": True,
                    "fetch_error": err,
                    "bytes": len(stale.encode("utf-8")),
                    "preview": stale[:400],
                    "warning": "network failed; using stale cache",
                }
            return {
                "ok": False,
                "error": err,
                "urls_tried": urls,
                "fallback": f"WebFetch {urls[0]} then write to {body.as_posix()}",
            }
        _write_cache(
            body,
            meta,
            text,
            {"id": source_id, "kind": kind, "url": used, "repo": src.get("repo"), "file": file_path},
        )
        return {
            "ok": True,
            "id": source_id,
            "kind": kind,
            "path": body.as_posix(),
            "cached": False,
            "url": used,
            "bytes": len(text.encode("utf-8")),
            "preview": text[:400],
            "instruction": "Prefer search-cache --q … on this path; avoid dumping entire file.",
        }

    return {"ok": False, "error": f"unsupported kind: {kind}"}


def search_cache(cache_root: Path, q: str, limit: int = 8, max_line: int = 240) -> Dict[str, Any]:
    q_l = (q or "").strip().lower()
    if not q_l:
        return {"ok": False, "error": "empty --q"}
    if not cache_root.is_dir():
        return {"ok": True, "hits": [], "note": "cache empty"}
    hits: List[Dict[str, Any]] = []
    for path in sorted(cache_root.rglob("*.md")):
        text = _read_text(path)
        for i, line in enumerate(text.splitlines(), start=1):
            if q_l in line.lower():
                hits.append(
                    {
                        "path": path.as_posix(),
                        "line": i,
                        "text": line.strip()[:max_line],
                    }
                )
                if len(hits) >= limit:
                    return {"ok": True, "q": q, "hits": hits}
    return {"ok": True, "q": q, "hits": hits}


def slice_file(path: Path, start: int, end: int) -> Dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": f"missing {path}"}
    lines = _read_text(path).splitlines()
    start = max(1, start)
    end = min(len(lines), max(start, end))
    chunk = lines[start - 1 : end]
    return {
        "ok": True,
        "path": path.as_posix(),
        "start": start,
        "end": end,
        "lines": chunk,
        "text": "\n".join(chunk),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="hs-dev-skill rule library fetch/search")
    p.add_argument("--skill-root", default="", help="override skill root")
    p.add_argument("--cache-root", default="", help="override rule cache dir")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list catalog sources")

    sp = sub.add_parser("search", help="search catalog by tags/when/id")
    sp.add_argument("--q", required=True)
    sp.add_argument("--limit", type=int, default=8)

    rp = sub.add_parser("resolve", help="resolve local path or fetch remote into cache")
    rp.add_argument("--id", required=True)
    rp.add_argument("--rule", default="", help="required for github_tree sources")
    rp.add_argument("--force", action="store_true")

    fp = sub.add_parser("fetch", help="force refresh remote source")
    fp.add_argument("--id", required=True)
    fp.add_argument("--rule", default="")

    sc = sub.add_parser("search-cache", help="grep lines in cached remote bodies")
    sc.add_argument("--q", required=True)
    sc.add_argument("--limit", type=int, default=8)

    sl = sub.add_parser("slice", help="slice a resolved/cached markdown file")
    sl.add_argument("--path", required=True)
    sl.add_argument("--start", type=int, default=1)
    sl.add_argument("--end", type=int, default=SLICE_DEFAULT)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ensure_utf8_stdout()
    args = build_parser().parse_args(argv)
    skill_root = Path(args.skill_root).resolve() if args.skill_root else skill_root_from_here()
    cache_root = Path(args.cache_root).resolve() if args.cache_root else rule_cache_dir()
    catalog = load_catalog(skill_root)

    if args.cmd == "list":
        print(json.dumps(list_sources(catalog), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "search":
        print(json.dumps(search_catalog(catalog, args.q, args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "resolve":
        out = resolve_source(
            skill_root,
            catalog,
            args.id,
            rule=(args.rule or None),
            force=bool(args.force),
            cache_root=cache_root,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 2
    if args.cmd == "fetch":
        out = resolve_source(
            skill_root,
            catalog,
            args.id,
            rule=(args.rule or None),
            force=True,
            cache_root=cache_root,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 2
    if args.cmd == "search-cache":
        print(json.dumps(search_cache(cache_root, args.q, args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "slice":
        print(json.dumps(slice_file(Path(args.path), args.start, args.end), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
