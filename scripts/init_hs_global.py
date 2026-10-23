#!/usr/bin/env python3
"""
init_hs_global.py
在用户主目录创建/对齐跨项目共享区（Windows / Linux / macOS）：

  Path.home() / ".hs-dev-skill"

包含：preferences.yaml、tech_learning/、learn_and_prefer.md 协议副本。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# 允许直接 python scripts/init_hs_global.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hs_paths import ensure_utf8_stdout, global_root, global_root_display  # noqa: E402


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_file_from_template(dest: Path, template: Path, *, overwrite: bool = False) -> str:
    if dest.exists() and not overwrite:
        return f"keep  {dest}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if template.exists():
        shutil.copy2(template, dest)
        return f"copy  {dest}"
    dest.write_text("", encoding="utf-8")
    return f"touch {dest}"


def init_hs_global(*, sync_protocol: bool = True) -> Path:
    ensure_utf8_stdout()
    root = global_root()
    templates = skill_root() / "resources" / "templates" / "hs_global"
    protocol_src = skill_root() / "references" / "learn_and_prefer.md"

    root.mkdir(parents=True, exist_ok=True)
    (root / "tech_learning").mkdir(parents=True, exist_ok=True)

    actions = [
        ensure_file_from_template(root / "_00_global_area_guide.md", templates / "_00_global_area_guide.md"),
        ensure_file_from_template(root / "preferences.yaml", templates / "preferences.yaml"),
        ensure_file_from_template(
            root / "tag_synonyms.yaml",
            templates / "tag_synonyms.yaml",
        ),
    ]

    if sync_protocol:
        if protocol_src.exists():
            shutil.copy2(protocol_src, root / "learn_and_prefer.md")
            actions.append(f"sync  {root / 'learn_and_prefer.md'}")
        else:
            actions.append("skip  learn_and_prefer.md (source missing)")

    note_tpl = templates / "tech_learning_notes.md"
    if note_tpl.exists():
        actions.append(
            ensure_file_from_template(
                root / "tech_learning" / "_TEMPLATE_notes.md",
                note_tpl,
            )
        )

    info = global_root_display()
    print(f"[*] hs-dev-skill global root ({info['platform']}): {info['resolved']}")
    print(f"    linux/mac: {info['linux_macos']}")
    print(f"    win cmd:   {info['windows_cmd']}")
    print(f"    win pwsh:  {info['windows_pwsh']}")
    for line in actions:
        print(f"  - {line}")

    # 重建全局标签索引（SQLite，三端标准库）
    try:
        from global_index_db import GlobalIndexDB

        db = GlobalIndexDB(root)
        try:
            db_info = db.rebuild()
        finally:
            db.close()
        print(
            f"[*] Global index rebuilt: notes+prefs={db_info.get('inserted', 0)}, "
            f"fts={db_info.get('fts')}, path={db_info.get('db_path')}"
        )
    except Exception as ex:
        print(f"[WARN] Global index rebuild skipped: {ex}")

    print("[SUCCESS] Global preference & tech-learning area ready (Windows / Linux / macOS).")
    print(
        "[NOTE] Search: python scripts/global_index_db.py search --tag 反向代理"
        "  (or --q nginx)"
    )
    return root


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize Path.home()/.hs-dev-skill for cross-project preferences "
            "and tech learning (Windows / Linux / macOS)"
        )
    )
    parser.add_argument(
        "--no-sync-protocol",
        action="store_true",
        help="Do not overwrite <global>/learn_and_prefer.md from Skill source",
    )
    args = parser.parse_args()
    init_hs_global(sync_protocol=not args.no_sync_protocol)


if __name__ == "__main__":
    main()
