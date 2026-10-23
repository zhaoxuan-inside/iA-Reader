#!/usr/bin/env python3
"""
plan_log / change_log 过程账本：续做扫描、checkpoint 快照、非 git 回退。
Windows / Linux / macOS；仅标准库。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from hs_paths import ensure_utf8_stdout
from idx_manager import IdxManager

ACTIVE_STATUSES = ("READY", "IN_PROGRESS", "BLOCKED", "VERIFYING")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S") + f"_{now.microsecond:06d}"


def docs_root(root: Path) -> Path:
    p_new = root / "hs_dev_docs" / "_06_dev_process"
    p_old = root / "hs_dev_docs" / "_08_dev_process"
    if p_new.exists() or not p_old.exists():
        return p_new
    return p_old


def plan_path(root: Path, task_id: str) -> Path:
    return docs_root(root) / "_01_plan_log" / f"{task_id}_plan.md"


def change_path(root: Path, task_id: str) -> Path:
    return docs_root(root) / "_02_change_log" / f"{task_id}_changes.jsonl"


def snap_root(root: Path, checkpoint_id: str) -> Path:
    return docs_root(root) / "_04_error_recovery" / "snapshots" / checkpoint_id


def _safe_snap_name(rel: str) -> str:
    return rel.replace("\\", "/").replace("/", "__")


def ensure_plan(
    root: Path,
    task_id: str,
    title: str = "",
    change_size: str = "M",
    work_mode: str = "IMPLEMENT",
    stage: str = "4",
    steps: Optional[Sequence[Tuple[str, str]]] = None,
) -> Path:
    path = plan_path(root, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    steps = list(steps) if steps else [("S1", "推进当前任务至下一可验证增量")]
    rows = "\n".join(
        f"| {sid} | {desc} | pending | |" for sid, desc in steps
    )
    first = steps[0][0]
    content = f"""# 任务计划账本：{task_id}

- **task_id**：`{task_id}`
- **标题**：{title or task_id}
- **change_size**：`{change_size}`
- **work_mode**：`{work_mode}`
- **当前阶段**：`{stage}`
- **断点**：`{first}` — {steps[0][1]}
- **更新时间**：`{_utc_now()}`

---

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
{rows}
"""
    path.write_text(content, encoding="utf-8")
    return path


def parse_plan(text: str) -> Dict[str, Any]:
    meta: Dict[str, str] = {}
    for key in ("task_id", "标题", "change_size", "work_mode", "当前阶段", "断点"):
        m = re.search(rf"-\s*\*\*{re.escape(key)}\*\*：`?([^`\n]+)`?", text)
        if m:
            meta[key] = m.group(1).strip()
    steps: List[Dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 3 or cols[0] in ("step_id", "---------"):
            continue
        if re.match(r"^-+$", cols[0].replace("-", "")):
            continue
        steps.append(
            {
                "step_id": cols[0],
                "desc": cols[1] if len(cols) > 1 else "",
                "status": cols[2] if len(cols) > 2 else "pending",
                "note": cols[3] if len(cols) > 3 else "",
            }
        )
    return {"meta": meta, "steps": steps}


def set_plan_step(
    root: Path,
    task_id: str,
    step_id: str,
    status: str,
    breakpoint: bool = True,
) -> Path:
    path = plan_path(root, task_id)
    if not path.exists():
        raise FileNotFoundError(f"plan_log missing: {path}")
    text = path.read_text(encoding="utf-8")
    parsed = parse_plan(text)
    lines = text.splitlines()
    new_lines: List[str] = []
    desc_for_bp = step_id
    for line in lines:
        if line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if cols and cols[0] == step_id and len(cols) >= 3:
                cols[2] = status
                desc_for_bp = cols[1] if len(cols) > 1 else step_id
                line = "| " + " | ".join(cols) + " |"
        if line.startswith("- **更新时间**："):
            line = f"- **更新时间**：`{_utc_now()}`"
        if breakpoint and line.startswith("- **断点**："):
            line = f"- **断点**：`{step_id}` — {desc_for_bp}"
        new_lines.append(line)
    # if step not found in table, still update breakpoint
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    _ = parsed
    return path


def read_changes(root: Path, task_id: str) -> List[Dict[str, Any]]:
    path = change_path(root, task_id)
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def append_change(root: Path, entry: Dict[str, Any]) -> Path:
    path = change_path(root, entry["task_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def checkpoint(
    root: Path,
    task_id: str,
    step_id: str,
    summary: str,
    paths: Sequence[str],
    status_before: str = "IN_PROGRESS",
) -> Dict[str, Any]:
    ensure_plan(root, task_id)
    cp_id = f"cp_{_stamp()}"
    snap_dir = snap_root(root, cp_id)
    snap_dir.mkdir(parents=True, exist_ok=True)
    path_entries: List[Dict[str, Any]] = []
    for raw in paths:
        rel = raw.replace("\\", "/").lstrip("./")
        abs_p = (root / rel).resolve()
        # 保证在 root 下
        try:
            abs_p.relative_to(root.resolve())
        except ValueError as e:
            raise ValueError(f"path outside root: {raw}") from e
        entry: Dict[str, Any] = {"path": rel}
        if abs_p.is_file():
            dest = snap_dir / _safe_snap_name(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_p, dest)
            # snapshot 路径相对 _08_dev_process，供 rollback 还原
            entry["snapshot"] = (
                f"_04_error_recovery/snapshots/{cp_id}/{_safe_snap_name(rel)}"
            )
        else:
            entry["created"] = True
        path_entries.append(entry)

    rec = {
        "checkpoint_id": cp_id,
        "task_id": task_id,
        "at": _utc_now(),
        "step_id": step_id,
        "summary": summary,
        "paths": path_entries,
        "status_before": status_before,
        "plan_step_before": step_id,
    }
    append_change(root, rec)
    set_plan_step(root, task_id, step_id, "doing", breakpoint=True)
    return rec


def rollback(root: Path, task_id: str, to_checkpoint: str) -> Dict[str, Any]:
    changes = read_changes(root, task_id)
    if not changes:
        raise FileNotFoundError(f"no change_log for {task_id}")

    idx = next(
        (i for i, c in enumerate(changes) if c.get("checkpoint_id") == to_checkpoint),
        None,
    )
    if idx is None:
        raise ValueError(f"checkpoint not found: {to_checkpoint}")

    # 逆序恢复 idx 及之后的条目（恢复到 to 之前 = 撤销 to 及其后）
    to_undo = list(reversed(changes[idx:]))
    restored: List[str] = []
    deleted: List[str] = []
    proc = docs_root(root)

    for rec in to_undo:
        for p in rec.get("paths") or []:
            rel = p["path"]
            abs_p = root / rel
            if p.get("created") and not p.get("snapshot"):
                if abs_p.is_file():
                    abs_p.unlink()
                    deleted.append(rel)
                continue
            snap_rel = p.get("snapshot")
            if not snap_rel:
                continue
            snap_abs = proc / snap_rel
            if not snap_abs.is_file():
                raise FileNotFoundError(f"missing snapshot: {snap_rel}")
            abs_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snap_abs, abs_p)
            restored.append(rel)

    # plan：断点回到 to 的 step，该步及之后标 pending
    plan_file = plan_path(root, task_id)
    target_step = changes[idx].get("step_id") or "S1"
    if plan_file.exists():
        parsed = parse_plan(plan_file.read_text(encoding="utf-8"))
        seen = False
        for st in parsed["steps"]:
            if st["step_id"] == target_step:
                seen = True
            if seen:
                set_plan_step(
                    root, task_id, st["step_id"], "pending", breakpoint=False
                )
        set_plan_step(root, task_id, target_step, "doing", breakpoint=True)

    rb_id = f"cp_{_stamp()}_rollback"
    rb_entry = {
        "checkpoint_id": rb_id,
        "task_id": task_id,
        "at": _utc_now(),
        "step_id": target_step,
        "summary": f"ROLLBACK to {to_checkpoint}",
        "paths": [{"path": r, "restored_from": to_checkpoint} for r in restored]
        + [{"path": d, "deleted": True} for d in deleted],
        "status_before": "IN_PROGRESS",
        "plan_step_before": target_step,
        "rollback_of": to_checkpoint,
    }
    append_change(root, rb_entry)

    status_note = None
    try:
        from task_manager import TaskManager

        TaskManager(str(root)).set_status(
            task_id,
            "IN_PROGRESS",
            note=f"rollback to {to_checkpoint}",
            force=True,
        )
        status_note = "IN_PROGRESS"
    except Exception as e:
        status_note = f"status_unchanged: {e}"

    return {
        "ok": True,
        "task_id": task_id,
        "to": to_checkpoint,
        "restored": restored,
        "deleted": deleted,
        "rollback_checkpoint": rb_id,
        "breakpoint": target_step,
        "task_status": status_note,
    }


def _active_tasks(root: Path) -> List[Dict[str, Any]]:
    idx = root / "hs_dev_docs/_05_task_orchestration/_00_task.idx"
    if not idx.exists():
        idx = root / "hs_dev_docs/_05_task_orchestration/_00_task.idx"
    if not idx.exists():
        return []
    mgr = IdxManager(str(idx))
    out: List[Dict[str, Any]] = []
    for e in mgr.entries:
        st = e.get("status") or ""
        if st in ACTIVE_STATUSES or st == "DRAFT":
            out.append(e)
    return out


def resume_scan(root: Path) -> Dict[str, Any]:
    tasks = _active_tasks(root)
    items = []
    for e in tasks:
        tid = e.get("id") or ""
        plan_p = plan_path(root, tid)
        plan_meta: Dict[str, Any] = {}
        if plan_p.exists():
            plan_meta = parse_plan(plan_p.read_text(encoding="utf-8"))
        changes = read_changes(root, tid)
        recent = changes[-5:] if changes else []
        items.append(
            {
                "task_id": tid,
                "title": e.get("title") or e.get("name") or "",
                "status": e.get("status"),
                "plan_exists": plan_p.exists(),
                "breakpoint": (plan_meta.get("meta") or {}).get("断点"),
                "recent_changes": [
                    {
                        "checkpoint_id": c.get("checkpoint_id"),
                        "summary": c.get("summary"),
                        "step_id": c.get("step_id"),
                    }
                    for c in recent
                ],
            }
        )
    return {"ok": True, "count": len(items), "tasks": items}


def _print(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="plan_log / change_log continuity")
    parser.add_argument("--root", default=".", help="workspace root")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ens = sub.add_parser("plan-ensure", help="Create plan_log if missing")
    p_ens.add_argument("--id", required=True)
    p_ens.add_argument("--title", default="")
    p_ens.add_argument("--change-size", default="M")
    p_ens.add_argument("--work-mode", default="IMPLEMENT")

    p_show = sub.add_parser("plan-show", help="Show parsed plan_log")
    p_show.add_argument("--id", required=True)

    p_set = sub.add_parser("plan-set-step", help="Update a plan step status")
    p_set.add_argument("--id", required=True)
    p_set.add_argument("--step", required=True)
    p_set.add_argument(
        "--status", required=True, choices=["pending", "doing", "done", "skipped"]
    )

    p_cp = sub.add_parser("checkpoint", help="Snapshot paths then append change_log")
    p_cp.add_argument("--id", required=True)
    p_cp.add_argument("--step", required=True)
    p_cp.add_argument("--summary", required=True)
    p_cp.add_argument(
        "--paths",
        required=True,
        help="Comma-separated paths relative to workspace root",
    )
    p_cp.add_argument("--status-before", default="IN_PROGRESS")

    p_rb = sub.add_parser("rollback", help="Non-git rollback using change_log snapshots")
    p_rb.add_argument("--id", required=True)
    p_rb.add_argument("--to", required=True, help="checkpoint_id to roll back to (inclusive undo)")

    p_rs = sub.add_parser("resume-scan", help="List active tasks + plan breakpoints")

    p_ch = sub.add_parser("change-list", help="List change_log entries")
    p_ch.add_argument("--id", required=True)
    p_ch.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "plan-ensure":
            p = ensure_plan(
                root,
                args.id,
                title=args.title,
                change_size=args.change_size,
                work_mode=args.work_mode,
            )
            _print({"ok": True, "path": str(p)})
        elif args.command == "plan-show":
            p = plan_path(root, args.id)
            if not p.exists():
                _print({"ok": False, "error": f"missing {p}"})
                return 1
            _print({"ok": True, **parse_plan(p.read_text(encoding="utf-8"))})
        elif args.command == "plan-set-step":
            p = set_plan_step(root, args.id, args.step, args.status)
            _print({"ok": True, "path": str(p)})
        elif args.command == "checkpoint":
            paths = [x.strip() for x in args.paths.split(",") if x.strip()]
            rec = checkpoint(
                root,
                args.id,
                args.step,
                args.summary,
                paths,
                status_before=args.status_before,
            )
            _print({"ok": True, "checkpoint": rec})
        elif args.command == "rollback":
            _print(rollback(root, args.id, args.to))
        elif args.command == "resume-scan":
            _print(resume_scan(root))
        elif args.command == "change-list":
            ch = read_changes(root, args.id)
            _print({"ok": True, "count": len(ch), "entries": ch[-args.limit :]})
        else:
            parser.error(f"unknown command {args.command}")
            return 2
    except Exception as e:
        _print({"ok": False, "error": str(e)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
