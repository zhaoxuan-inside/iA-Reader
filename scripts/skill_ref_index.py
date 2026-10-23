#!/usr/bin/env python3
"""
Skill references 场景索引（Windows / Linux / macOS）。

权威源：skill 包内 references/*.md
SQLite 缓存：<skill_root>/.hs_cache/skill_ref.sqlite（可重建，勿手改）

用途：不确定读哪份详规时先 search，禁止通读 references/。
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from hs_paths import ensure_utf8_stdout

SUMMARY_MAX = 400
BODY_MAX = 8000
DEFAULT_LIMIT = 8
CACHE_DIR_NAME = ".hs_cache"
DB_FILE_NAME = "skill_ref.sqlite"

# 文件名 → 场景关键词（补充 _index 与文首「何时读」）
FILE_SCENARIOS: Dict[str, List[str]] = {
    "_index.md": ["index", "路由", "目录", "入口"],
    "load_latch.md": ["门闩", "装载", "反合理化", "latch", "跳过", "强制"],
    "right_sizing.md": ["分级", "S", "M", "L", "快路径", "小改动", "right-sizing", "change_size"],
    "token_budget.md": [
        "token", "预算", "context_pack", "装载", "SQLite", "doc_index_db", "切片", "免通读", "免扫描",
    ],
    "reverse_engineering.md": [
        "反向工程", "反向重建", "逆向", "reverse", "已有项目", "存量项目", "brownfield", "遗留代码", "规范接入", "架构还原",
    ],
    "systematic_debugging.md": [
        "调试", "bug", "修复", "fix", "排查", "先红后绿", "复现", "回归", "异常", "崩溃", "debugging", "根因分析", "RCA",
    ],
    "code_refactoring.md": [
        "重构", "refactor", "refactoring", "坏味道", "消除坏味道", "等价演进", "特征测试", "保护网", "行为等价", "深模块演进",
    ],
    "code_exploration.md": [
        "代码理解", "探索", "只读", "explore", "时序图", "调用链", "架构理解", "答疑", "咨询", "只读理解", "comprehension",
    ],
    "coding_standards.md": [
        "编码规范", "规范", "linter", "命名", "静态检测", "词态矩阵", "单一事实源", "零裸字符串", "coding_standards", "规范门禁",
    ],
    "method_archetypes.md": [
        "方法设计", "方法画像", "七分类", "archetype", "契约画像", "写前检索", "抗方法爆炸", "影子函数", "单一天理源",
    ],
    "auxiliary_governance.md": [
        "工程治理", "治理", "governance", "机密隔离", "供应链", "安全", "容灾", "cicd", "可观测性", "探针", "功能开关", "governance_toggle",
    ],
    "grill_orchestration.md": [
        "grill", "grilling", "审讯", "对齐", "澄清", "设计树", "多问", "DESIGN",
        "office-hours", "方案比选", "trade-offs",
    ],
    "testing.md": [
        "测试", "TDD", "seam", "质量", "单测", "红绿", "契约测", "test", "coverage",
    ],
    "deep_modules.md": [
        "深模块", "deep", "module", "seam", "adapter", "删除测试", "深度",
        "Ousterhout", "重构", "接口", "leverage", "locality",
    ],
    "frontend_aesthetic.md": [
        "审美", "aesthetic", "Anthropic", "frontend-design", "默认审美",
        "typography", "hero", "反模板", "AI皮",
    ],
    "design_md.md": [
        "DESIGN.md", "设计", "视觉", "品牌", "design-md", "Stitch",
        "awesome-design-md", "对标", "token", "氛围", "Stripe", "Linear",
    ],
    "frontend_craft.md": [
        "前端", "UI", "组件", "页面", "a11y", "React", "样式",
        "anti-slop", "动效", "motion", "hero", "无障碍", "手艺",
    ],
    "dev_paradigm.md": [
        "范式", "开发范式", "规模", "类型", "选型", "阶梯",
        "事务脚本", "模块化单体", "CRUD", "B2B", "产品形态",
    ],
    "ddd_design.md": [
        "DDD", "领域", "限界上下文", "聚合", "统一语言", "上下文映射",
        "战略", "战术", "领域驱动", "bounded context", "aggregate",
    ],
    "frontend_arch.md": [
        "前端架构", "FSD", "feature-sliced", "模块", "feature", "BFF",
        "切片", "前端分层",
    ],
    "backend_arch.md": [
        "后端", "架构", "分层", "hexagonal", "clean",
        "微服务", "saga", "补偿", "ports", "adapter", "框架设计",
    ],
    "api_engineering.md": ["API", "接口", "契约", "幂等", "Mock", "REST", "错误码"],
    "rule_library.md": [
        "规则库", "rule_fetch", "远程规则", "Vercel", "Anthropic", "Addy",
        "anti-slop", "Lottie", "ui-craft", "web-interface", "DESIGN.md",
        "awesome-design-md", "wshobson", "Clean Architecture", "DDD", "FSD",
        "gstack", "pm-skills", "ui-ux-pro-max",
    ],
    "confidence_decision.md": [
        "置信度", "询问", "闸门", "决策", "DESIGN", "IMPLEMENT",
        "设计多问", "实现少问", "审讯", "跳过澄清", "跳过",
    ],
    "process_continuity.md": [
        "继续", "续做", "继续任务", "resume", "plan_log", "change_log",
        "回退", "rollback", "checkpoint", "中断", "过程日志",
    ],
    "product_design.md": [
        "产品设计", "设计语言", "产品功能", "PRD", "功能规格", "design tokens",
        "UI规范", "功能架构", "用户旅程", "四态", "产品设计规范", "tokens",
        "JTBD", "Gherkin", "渐进式披露", "微文案", "冷启动", "FTUE", "Aha Moment",
        "Status Quo", "痛点", "产品探索", "体验评审",
    ],
    "product_prototype.md": [
        "原型", "线框", "mermaid", "figma", "布局", "prototype",
        "商业计划", "无图", "多态", "ASCII", "ASCII线框", "双轨原型", "wireframe",
    ],
    "product_roadmap.md": [
        "MVP", "分阶段规划", "分阶段实施", "产品开发分阶段规划书", "roadmap",
        "规划书", "功能裁剪", "MoSCoW", "人机交互", "演进路线", "里程碑",
    ],
    "learn_and_prefer.md": ["学习", "偏好", "GitHub", "对标", "标签"],
    "spec_driven_lifecycle.md": ["生命周期", "阶段", "门禁", "PRD", "冻结", "原型"],
    "six_tuple_runtime.md": ["六元组", "compensate", "fallback", "metrics", "recall"],
    "four_level_routing.md": [
        "四级索引", "JSONL", "路由", "底层真理", "检索", "调用图", "依赖图", "代码切片", "索引路由",
    ],
    "task_state_machine.md": ["任务", "状态机", "handoff", "迁移", "ABORTED"],
    "mock_contract_guide.md": ["Mock", "Profile", "契约测试"],
    "quality_gates.md": ["门禁", "verify", "提交前", "覆盖率", "九级"],
    "version_control.md": [
        "版本", "版本号", "version", "semver", "发布", "release", "tag", "升级",
        "防漂移", "单源", "变更分级", "补丁", "major", "minor", "patch",
    ],
    "design_patterns.md": [
        "设计模式", "模式", "策略模式", "责任链", "状态模式", "建造者", "适配器",
        "门面", "外观", "发布订阅", "观察者", "模板方法", "模式集群", "pattern",
        "cluster", "防破坏", "vibecoding", "深模块", "反过度设计",
    ],
    "cross_platform.md": ["跨平台", "Windows", "Linux", "macOS", "pathlib"],
    "doc_reading_guide.md": [
        "文档阅读说明", "阅读说明", "文档体系", "索引导航", "doc_reading_guide",
        "reading_guide", "跨Agent", "Agent协同", "全局索引", "README.md",
    ],
    "spec_v2_4.md": ["规格", "百科", "争议"],
}


def skill_root_from_here() -> Path:
    """scripts/ 的上一级即为 skill 根（含 SKILL.md）。"""
    here = Path(__file__).resolve().parent
    candidate = here.parent
    if (candidate / "SKILL.md").is_file():
        return candidate
    # 回退：向上找
    for parent in here.parents:
        if (parent / "SKILL.md").is_file() and (parent / "references").is_dir():
            return parent
    return candidate


def db_path_for_skill(skill_root: Path) -> Path:
    return (skill_root / CACHE_DIR_NAME / DB_FILE_NAME).resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


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
        if not s:
            continue
        if s.startswith("#"):
            lines.append(s.lstrip("#").strip())
            continue
        if s.startswith("```") or s.startswith("---") or s.startswith("|"):
            continue
        lines.append(s)
        if sum(len(x) for x in lines) >= SUMMARY_MAX:
            break
    summary = " ".join(lines).strip() or (title or text[:SUMMARY_MAX])
    return summary[:SUMMARY_MAX]


def _when_to_read(text: str) -> str:
    m = re.search(r"(?m)^\*\*何时读\*\*[：:]\s*(.+)$", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?m)^何时读[：:]\s*(.+)$", text)
    if m:
        return m.group(1).strip()
    return ""


def _parse_index_scenarios(index_text: str) -> Dict[str, List[str]]:
    """从 _index.md 表格行提取 filename → 场景短语。"""
    out: Dict[str, List[str]] = {}
    for line in index_text.splitlines():
        if "`" not in line or "|" not in line:
            continue
        # | 场景 | `file.md` |
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        scenario, file_cell = cells[0], cells[1]
        fm = re.search(r"`([^`]+\.md)`", file_cell)
        if not fm:
            continue
        name = fm.group(1)
        if name.startswith("_") and name != "_index.md":
            pass
        tags = [scenario] + re.findall(r"[\w\u4e00-\u9fff/-]+", scenario)
        out.setdefault(name, []).extend(tags)
    return out


def _unique_tags(tags: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for t in tags:
        t = (t or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


class SkillRefIndex:
    def __init__(self, skill_root: Optional[Path] = None):
        self.skill_root = Path(skill_root).resolve() if skill_root else skill_root_from_here()
        self.ref_dir = self.skill_root / "references"
        self.db_path = db_path_for_skill(self.skill_root)
        self.fts_available = False
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refs (
                path TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT,
                body TEXT,
                tags TEXT,
                when_to_read TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        self.fts_available = self._try_fts(conn)
        self._conn = conn
        return conn

    def _try_fts(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("DROP TABLE IF EXISTS refs_fts")
            conn.execute(
                """
                CREATE VIRTUAL TABLE refs_fts USING fts5(
                    path UNINDEXED,
                    title,
                    summary,
                    body,
                    tags,
                    when_to_read,
                    tokenize='unicode61'
                )
                """
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def rebuild(self) -> Dict[str, Any]:
        if not self.ref_dir.is_dir():
            return {
                "ok": False,
                "error": f"references/ not found under {self.skill_root}",
            }
        conn = self.connect()
        conn.execute("DELETE FROM refs")
        if self.fts_available:
            try:
                conn.execute("DELETE FROM refs_fts")
            except sqlite3.Error:
                self.fts_available = False

        index_scenarios = {}
        index_path = self.ref_dir / "_index.md"
        if index_path.is_file():
            index_scenarios = _parse_index_scenarios(_read_text(index_path))

        inserted = 0
        for path in sorted(self.ref_dir.glob("*.md")):
            text = _read_text(path)
            title_m = re.search(r"(?m)^#\s+(.+)$", text)
            title = title_m.group(1).strip() if title_m else path.stem
            when = _when_to_read(text)
            tags = list(FILE_SCENARIOS.get(path.name, []))
            tags.extend(index_scenarios.get(path.name, []))
            if when:
                tags.append(when)
            tags = _unique_tags(tags)
            summary = _extract_summary(text, title)
            tag_str = " ".join(tags)
            conn.execute(
                """
                INSERT OR REPLACE INTO refs(path, title, summary, body, tags, when_to_read, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"references/{path.name}",
                    title,
                    summary,
                    text[:BODY_MAX],
                    tag_str,
                    when,
                    _utc_now(),
                ),
            )
            if self.fts_available:
                conn.execute(
                    """
                    INSERT INTO refs_fts(path, title, summary, body, tags, when_to_read)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"references/{path.name}",
                        title,
                        summary,
                        text[:BODY_MAX],
                        tag_str,
                        when,
                    ),
                )
            inserted += 1

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("rebuilt_at", _utc_now()),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("fts", "1" if self.fts_available else "0"),
        )
        conn.commit()
        payload = {
            "ok": True,
            "skill_root": str(self.skill_root),
            "db_path": str(self.db_path),
            "inserted": inserted,
            "fts": self.fts_available,
            "rebuilt_at": _utc_now(),
        }
        self.close()
        return payload

    def search(
        self,
        q: str = "",
        tag: str = "",
        scenario: str = "",
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        conn = self.connect()
        limit = max(1, min(int(limit or DEFAULT_LIMIT), 50))
        needle = " ".join(x for x in [q, tag, scenario] if x).strip()
        if not needle:
            rows = conn.execute(
                "SELECT path, title, summary, tags, when_to_read FROM refs ORDER BY path LIMIT ?",
                (limit,),
            ).fetchall()
            return {
                "ok": True,
                "query": needle,
                "count": len(rows),
                "hits": [dict(r) for r in rows],
            }

        hits: List[Dict[str, Any]] = []
        use_like = _has_cjk(needle) or not self.fts_available
        if not use_like and self.fts_available:
            try:
                # FTS: OR tokens lightly
                tokens = [t for t in re.split(r"\s+", needle) if t]
                fts_q = " OR ".join(f'"{t}"' if " " in t else t for t in tokens) or needle
                rows = conn.execute(
                    """
                    SELECT r.path, r.title, r.summary, r.tags, r.when_to_read
                    FROM refs_fts f
                    JOIN refs r ON r.path = f.path
                    WHERE f MATCH ?
                    LIMIT ?
                    """,
                    (fts_q, limit),
                ).fetchall()
                hits = [dict(r) for r in rows]
            except sqlite3.Error:
                use_like = True

        if use_like or not hits:
            like = f"%{needle}%"
            # 多 token AND-ish：逐词 LIKE 过滤
            tokens = [t for t in re.split(r"\s+", needle) if t]
            sql = "SELECT path, title, summary, tags, when_to_read FROM refs WHERE 1=1"
            params: List[Any] = []
            for t in tokens:
                sql += " AND (title LIKE ? OR summary LIKE ? OR tags LIKE ? OR when_to_read LIKE ? OR body LIKE ?)"
                like_t = f"%{t}%"
                params.extend([like_t, like_t, like_t, like_t, like_t])
            sql += " ORDER BY path LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            hits = [dict(r) for r in rows]

        return {"ok": True, "query": needle, "count": len(hits), "hits": hits}

    def stats(self) -> Dict[str, Any]:
        conn = self.connect()
        n = conn.execute("SELECT COUNT(*) AS c FROM refs").fetchone()["c"]
        rebuilt = conn.execute(
            "SELECT value FROM meta WHERE key='rebuilt_at'"
        ).fetchone()
        return {
            "ok": True,
            "count": n,
            "fts": self.fts_available,
            "db_path": str(self.db_path),
            "rebuilt_at": rebuilt["value"] if rebuilt else None,
        }


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ensure_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Index hs-dev-skill references/ for scenario routing (Win/Linux/macOS)"
    )
    parser.add_argument(
        "--skill-root",
        default="",
        help="Override skill root (default: parent of scripts/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rebuild", help="Rebuild references SQLite index")
    sub.add_parser("stats", help="Show index stats")

    p_search = sub.add_parser("search", help="Search references by query/tag/scenario")
    p_search.add_argument("--q", default="", help="Free text")
    p_search.add_argument("--tag", default="", help="Tag keyword")
    p_search.add_argument("--scenario", default="", help="Scenario phrase e.g. 幂等 / UI")
    p_search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    args = parser.parse_args(argv)
    root = Path(args.skill_root).resolve() if args.skill_root else None
    db = SkillRefIndex(root)
    try:
        if args.command == "rebuild":
            _print_json(db.rebuild())
            return 0
        if args.command == "stats":
            if not db.db_path.exists():
                db.rebuild()
                db = SkillRefIndex(root)
            _print_json(db.stats())
            return 0
        if args.command == "search":
            if not db.db_path.exists():
                db.rebuild()
                db = SkillRefIndex(root)
            _print_json(
                db.search(
                    q=args.q,
                    tag=args.tag,
                    scenario=args.scenario,
                    limit=args.limit,
                )
            )
            return 0
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
