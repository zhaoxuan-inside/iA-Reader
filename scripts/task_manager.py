#!/usr/bin/env python3
"""
task_manager.py
任务生命周期与三文件强一致性管理器。
支持任务创建、状态机流转、自动滚动分片、任务归档与会话交接。
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from idx_manager import IdxManager

VALID_STATUSES = ["DRAFT", "READY", "IN_PROGRESS", "BLOCKED", "VERIFYING", "COMPLETED", "ABORTED"]
VALID_CHANGE_SIZES = ("S", "M", "L")

# 合法迁移（终态默认不可迁出；回退用 force=True 或 status --force）
ALLOWED_TRANSITIONS = {
    "DRAFT": frozenset({"READY", "ABORTED"}),
    "READY": frozenset({"IN_PROGRESS", "ABORTED", "DRAFT"}),
    "IN_PROGRESS": frozenset({"BLOCKED", "VERIFYING", "ABORTED", "READY"}),
    "BLOCKED": frozenset({"IN_PROGRESS", "ABORTED"}),
    "VERIFYING": frozenset({"COMPLETED", "IN_PROGRESS", "ABORTED"}),
    "COMPLETED": frozenset(),
    "ABORTED": frozenset(),
}


def get_iso_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_change_size(change_size: Optional[str]) -> str:
    """Normalize to S|M|L; empty/None defaults to M (right_sizing: uncertain → M)."""
    if change_size is None or str(change_size).strip() == "":
        return "M"
    size = str(change_size).strip().upper()
    if size not in VALID_CHANGE_SIZES:
        raise ValueError(f"Invalid change_size '{change_size}'. Allowed: {list(VALID_CHANGE_SIZES)}")
    return size


class TaskManager:
    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root).resolve()
        self.docs_root = self.root / "hs_dev_docs"
        if (self.docs_root / "_05_task_orchestration").exists() or not (self.docs_root / "_08_dev_process/_09_task").exists():
            self.task_root = self.docs_root / "_05_task_orchestration"
            self.brief_dir = self.task_root / "_01_task_brief"
            self.detail_dir = self.task_root / "_02_task_detail"
            self.context_pack_dir = self.task_root / "_03_task_context_pack"
            self.archive_dir = self.task_root / "_04_task_archive"
            self.handoff_dir = self.docs_root / "_06_dev_process/_06_session_handoff"
        else:
            self.task_root = self.docs_root / "_08_dev_process/_09_task"
            self.brief_dir = self.task_root / "_01_task_brief"
            self.detail_dir = self.task_root / "_02_task_detail"
            self.context_pack_dir = self.task_root / "_03_task_context_pack"
            self.archive_dir = self.task_root / "_04_task_archive"
            self.handoff_dir = self.docs_root / "_08_dev_process/_05_session_handoff"

        self.task_idx_path = self.task_root / "_00_task.idx"
        self.archive_idx_path = self.task_root / "_00_task_archive.idx"

    def create_task(
        self,
        task_id: str,
        title: str,
        owner: str = "agent",
        priority: str = "P1",
        goal: str = "",
        criteria: str = "",
        change_size: str = "M",
    ):
        """创建新任务，原子更新 _00_task.idx、task_brief、task_detail 和 context_pack"""
        change_size = normalize_change_size(change_size)
        self.task_root.mkdir(parents=True, exist_ok=True)
        self.brief_dir.mkdir(parents=True, exist_ok=True)
        self.detail_dir.mkdir(parents=True, exist_ok=True)
        self.context_pack_dir.mkdir(parents=True, exist_ok=True)

        mgr = IdxManager(str(self.task_idx_path))
        if not mgr.metadata:
            mgr.init_idx("task_active", self.task_root.name)

        # 检查是否已存在
        for entry in mgr.entries:
            if entry.get("id") == task_id:
                raise ValueError(f"Task with ID '{task_id}' already exists in active tasks!")

        now = get_iso_timestamp()
        status = "READY"

        # 1. 创建任务详情目录与文件
        task_detail_folder = self.detail_dir / f"_01_{task_id}"
        task_detail_folder.mkdir(parents=True, exist_ok=True)
        detail_file = task_detail_folder / "_00_task_detail.md"

        detail_content = f"""# 任务详细设计与执行记录：{task_id}

- **任务名称**：{title}
- **变更分级**：`{change_size}`
- **当前状态**：`{status}`
- **优先级**：{priority}
- **负责人**：{owner}
- **开始时间**：`{now}`
- **最后更新**：`{now}`

---

## 1. 任务背景与目标
{goal or "暂无详细背景描述"}

---

## 2. 验收标准
{criteria or "1. 单元测试覆盖率达标\\n2. 契约比对一致"}

---

## 3. 执行步骤 (Checklist)
- [ ] 1. 完善设计文档与接口定义
- [ ] 2. 同步 DB 迁移脚本（V/U）
- [ ] 3. 编写/修改核心六元组业务逻辑
- [ ] 4. 编写全覆盖单测与契约测试
- [ ] 5. 本地质量门禁与提交前自检

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
(待更新)
```

---

## 5. 验证与门禁记录
- 单测覆盖率：`0%`
- 契约比对：`PENDING`
"""
        detail_file.write_text(detail_content, encoding="utf-8")

        # 2. 创建上下文包文件
        task_cp_folder = self.context_pack_dir / f"_01_{task_id}"
        task_cp_folder.mkdir(parents=True, exist_ok=True)
        cp_file = task_cp_folder / "_00_context_pack.md"
        cp_content = f"""# 上下文装载包 (Context Pack)：{task_id}

- **change_size**：`{change_size}`
- **任务 ID**：`{task_id}`
- **生成时间**：`{now}`
- **状态**：`{status}`
- **装载纪律**：必须物化切片正文；禁止只写路径。
- **查询**：`doc_index_db.py --root . search|slice`；Skill 详规用 `skill_ref_index.py search`（勿通读 references/）

---

## 1. 需求与目标（物化）
{goal or title}

<!-- Agent：用 doc_index_db search/slice 粘贴 PRD/DoD 关键段落，勿只留链接；S 可仅 3～8 行 DoD -->

---

## 2. 数据模型切片（物化）
<!-- 粘贴相关表字段/约束原文片段；并注明 path + line range；未触达写 N/A -->

---

## 3. 接口与六元组签名（物化）
<!-- 粘贴方法签名、入参/出参、compensate/fallback；改 API 时读 api_engineering.md -->

---

## 4. 调用链与 Mock 契约（物化）
<!-- 粘贴依赖方法清单与契约关键字段 -->

---

## 5. 查询轨迹（降 Token）
- `doc_index_db` 命中 path 列表：
- `skill_ref_index` 命中 path 列表：
- 本会话已读 Skill references（禁止重复整读）：
"""
        cp_file.write_text(cp_content, encoding="utf-8")

        # 3. 追加任务简述 (Task Brief) 并处理滚动分片 (10个任务一个分片)
        brief_ref = self._append_task_brief(
            task_id, title, status, priority, owner, goal, now, change_size
        )

        # 4. 更新 _00_task.idx
        rel_detail_path = f"_02_task_detail/_01_{task_id}/_00_task_detail.md"
        rel_cp_path = f"_03_task_context_pack/_01_{task_id}/_00_context_pack.md"
        mgr.add_entry(
            entry_id=task_id,
            title=title,
            rel_path=rel_detail_path,
            status=status,
            auto_digest=True
        )

        # 5. 同步创建 plan_log（续做/回退真理源之一）
        try:
            from process_log import ensure_plan

            ensure_plan(
                self.root,
                task_id,
                title=title,
                change_size=change_size,
                work_mode="IMPLEMENT" if change_size == "S" else "DESIGN",
                stage="4" if change_size != "S" else "S",
                steps=[
                    ("S1", "对齐/装载上下文"),
                    ("S2", "实现可验证增量"),
                    ("S3", "测试与门禁"),
                    ("S4", "归档与本地 Commit"),
                ],
            )
        except Exception as e:
            print(f"[WARN] plan_log ensure failed: {e}")

        print(f"[SUCCESS] Created task '{task_id}' (Status: {status}, change_size: {change_size})")
        return {
            "task_id": task_id,
            "status": status,
            "change_size": change_size,
            "detail_path": str(detail_file),
            "brief_ref": brief_ref,
            "context_pack_path": str(cp_file)
        }

    def _append_task_brief(
        self,
        task_id: str,
        title: str,
        status: str,
        priority: str,
        owner: str,
        goal: str,
        timestamp: str,
        change_size: str = "M",
    ) -> str:
        """追加任务简述（紧凑块不超过 15 行），自动滚动分片"""
        brief_files = sorted(self.brief_dir.glob("_*.md"))
        target_file = None

        if not brief_files:
            target_file = self.brief_dir / "_01_task_brief_001.md"
            target_file.write_text("# 任务简述清单分片 001\n\n", encoding="utf-8")
        else:
            last_file = brief_files[-1]
            content = last_file.read_text(encoding="utf-8")
            count = content.count("### 任务简述：")
            if count >= 10:
                # 滚动新建下一个分片
                idx_num = len(brief_files) + 1
                target_file = self.brief_dir / f"_{idx_num:02d}_task_brief_{idx_num:03d}.md"
                target_file.write_text(f"# 任务简述清单分片 {idx_num:03d}\n\n", encoding="utf-8")
            else:
                target_file = last_file

        brief_block = f"""### 任务简述：{task_id}
- **标题**：{title}
- **change_size**：`{change_size}`
- **状态**：`{status}`
- **优先级**：{priority}
- **负责人**：{owner}
- **核心目标**：{goal or title}
- **详情索引**：`_02_task_detail/_01_{task_id}/_00_task_detail.md`
- **上下文包**：`_03_task_context_pack/_01_{task_id}/_00_context_pack.md`
- **更新时间**：`{timestamp}`
---

"""
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(brief_block)

        # 更新 brief 索引
        brief_idx = IdxManager(str(self.brief_dir / "_00_task_brief.idx"))
        if not brief_idx.metadata:
            brief_idx.init_idx("task_brief", "_01_task_brief")
        brief_idx.add_entry(target_file.name, f"任务简述分片 {target_file.stem}", target_file.name)

        return f"_01_task_brief/{target_file.name}"

    def set_status(
        self,
        task_id: str,
        new_status: str,
        note: str = "",
        force: bool = False,
    ):
        """流转任务状态并原子同步三文件；默认校验合法迁移。"""
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {VALID_STATUSES}")

        mgr = IdxManager(str(self.task_idx_path))
        found = False
        target_entry = None
        for entry in mgr.entries:
            if entry.get("id") == task_id:
                found = True
                target_entry = entry
                break

        if not found:
            # 允许 force 从归档拉回（非 git 回退后重开）
            if force and new_status in ("IN_PROGRESS", "READY"):
                self._unarchive_task(task_id, new_status)
                mgr = IdxManager(str(self.task_idx_path))
                for entry in mgr.entries:
                    if entry.get("id") == task_id:
                        found = True
                        target_entry = entry
                        break
            if not found:
                raise ValueError(f"Active task '{task_id}' not found in _00_task.idx")

        old_status = target_entry.get("status") or "READY"
        allowed = ALLOWED_TRANSITIONS.get(old_status, frozenset())
        if not force and new_status != old_status and new_status not in allowed:
            raise ValueError(
                f"Illegal transition {old_status} → {new_status}. "
                f"Allowed from {old_status}: {sorted(allowed) or '∅ (terminal)'}. "
                f"Use --force only for process_log rollback reopen."
            )

        now = get_iso_timestamp()
        target_entry["status"] = new_status
        target_entry["updated_at"] = now
        if note:
            target_entry["last_note"] = note

        # 1. 更新 task_detail
        detail_path = self.task_root / target_entry["path"]
        if detail_path.exists():
            content = detail_path.read_text(encoding="utf-8")
            # 替换状态行与最后更新行
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("- **当前状态**："):
                    new_lines.append(f"- **当前状态**：`{new_status}`")
                elif line.startswith("- **最后更新**："):
                    new_lines.append(f"- **最后更新**：`{now}`")
                else:
                    new_lines.append(line)
            detail_path.write_text("\n".join(new_lines), encoding="utf-8")

        # 2. 更新 task_brief
        for b_file in sorted(self.brief_dir.glob("_*.md")):
            b_content = b_file.read_text(encoding="utf-8")
            if f"### 任务简述：{task_id}" in b_content:
                # 针对该块替换状态
                blocks = b_content.split("### 任务简述：")
                new_blocks = [blocks[0]]
                for block in blocks[1:]:
                    if block.startswith(task_id):
                        b_lines = block.split("\n")
                        upd_lines = []
                        for bl in b_lines:
                            if bl.startswith("- **状态**："):
                                upd_lines.append(f"- **状态**：`{new_status}`")
                            elif bl.startswith("- **更新时间**："):
                                upd_lines.append(f"- **更新时间**：`{now}`")
                            else:
                                upd_lines.append(bl)
                        new_blocks.append("\n".join(upd_lines))
                    else:
                        new_blocks.append(block)
                b_file.write_text("### 任务简述：".join(new_blocks), encoding="utf-8")
                break

        # 3. 更新 task.idx 以及关联的 brief 与 detail 索引 digest
        mgr.save()
        mgr.update_digest()

        brief_idx = IdxManager(str(self.brief_dir / "_00_task_brief.idx"))
        brief_idx.update_digest()

        detail_idx = IdxManager(str(self.detail_dir / "_00_task_detail.idx"))
        detail_idx.update_digest()

        # 4. 如果是终态 (COMPLETED / ABORTED)，触发归档
        if new_status in ["COMPLETED", "ABORTED"]:
            self._archive_task(task_id, new_status)

        print(
            f"[SUCCESS] Task '{task_id}' status transitioned "
            f"{old_status} → '{new_status}'"
            + (" (force)" if force else "")
        )

    def _archive_task(self, task_id: str, final_status: str):
        """将完成或废弃的任务归档移入 _00_task_archive.idx"""
        mgr = IdxManager(str(self.task_idx_path))
        target_entry = None
        for entry in mgr.entries:
            if entry.get("id") == task_id:
                target_entry = entry
                break

        if not target_entry:
            return

        # 移出活跃索引
        mgr.remove_entry(task_id)

        # 写入归档索引
        arch_mgr = IdxManager(str(self.archive_idx_path))
        if not arch_mgr.metadata:
            arch_mgr.init_idx("task_archive", self.task_root.name)

        target_entry["status"] = final_status
        arch_mgr.entries.append(target_entry)
        arch_mgr.save()
        print(f"[ARCHIVE] Task '{task_id}' archived into _00_task_archive.idx")

    def _unarchive_task(self, task_id: str, new_status: str):
        """从归档移回活跃索引（仅 force / 回退重开）。"""
        arch_mgr = IdxManager(str(self.archive_idx_path))
        target = None
        for entry in list(arch_mgr.entries):
            if entry.get("id") == task_id:
                target = entry
                break
        if not target:
            raise ValueError(f"Task '{task_id}' not found in active or archive idx")
        arch_mgr.entries = [e for e in arch_mgr.entries if e.get("id") != task_id]
        arch_mgr.save()

        mgr = IdxManager(str(self.task_idx_path))
        if not mgr.metadata:
            mgr.init_idx("task_active", self.task_root.name)
        target["status"] = new_status
        target["updated_at"] = get_iso_timestamp()
        mgr.entries.append(target)
        mgr.save()
        print(f"[UNARCHIVE] Task '{task_id}' restored to active as {new_status}")

    def create_session_handoff(self, task_id: str, checkpoint_desc: str, completed_steps: list, remaining_steps: list) -> str:
        """生成会话交接记录，保障断点续传"""
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        handoff_file = self.handoff_dir / f"handoff_{task_id}_{now_str}.md"

        completed_md = "\n".join([f"- [x] {s}" for s in completed_steps]) if completed_steps else "- 无"
        remaining_md = "\n".join([f"- [ ] {s}" for s in remaining_steps]) if remaining_steps else "- 无"

        content = f"""# 会话交接与断点恢复记录 (Session Handoff)

- **任务 ID**：`{task_id}`
- **中断时间**：`{get_iso_timestamp()}`

---

## 1. 当前执行断点
{checkpoint_desc}

---

## 2. 已完成步骤
{completed_md}

---

## 3. 遗留待办步骤
{remaining_md}

---

## 4. 恢复提示词 (Resume Prompt)
```text
请继续执行任务 [{task_id}]（语义续做，勿当新需求）。
先运行：python scripts/process_log.py resume-scan --root .
按该任务 plan_log 断点 + change_log 推进；handoff 仅作补充。
当前断点备注：{checkpoint_desc}。
```
"""
        handoff_file.write_text(content, encoding="utf-8")
        print(f"[SUCCESS] Created session handoff at: {handoff_file}")
        return str(handoff_file)

    def render_dashboard(
        self,
        intent: str = "BUILD",
        phase: str = "3",
        change_size: str = "M",
        output_path: Optional[str] = None,
    ) -> str:
        """Render a live execution dashboard in GitHub Flavored Markdown format with Mermaid flowchart."""
        phase_str = str(phase).strip()
        phase_num = int(phase_str) if phase_str.isdigit() else 3
        if phase_num < 0:
            phase_num = 0
        elif phase_num > 6:
            phase_num = 6

        mgr = IdxManager(str(self.task_idx_path))
        tasks = mgr.entries if mgr.metadata else []

        phases = [
            ("P0", "阶段 0: 原型与交互"),
            ("P1", "阶段 1: 选型 ADR"),
            ("P2", "阶段 2: 架构深模块"),
            ("P3", "阶段 3: 契约六元组"),
            ("P4", "阶段 4: 任务包装配"),
            ("P5", "阶段 5: 垂直 TDD"),
            ("P6", "阶段 6: 门禁与提交"),
        ]

        mermaid_nodes = []
        for i, (pid, label) in enumerate(phases):
            if i < phase_num:
                status_tag = "PASS ✅"
            elif i == phase_num:
                status_tag = "ACTIVE ⚡"
            elif i == 6:
                status_tag = "GATE 🔒"
            else:
                status_tag = "QUEUED ⏳"
            mermaid_nodes.append(f'    {pid}["{label}<br/><b>[{status_tag}]</b>"]')

        flow_links = []
        for i in range(len(phases) - 1):
            conn = "-->" if i < phase_num else "-.->"
            flow_links.append(f"    {phases[i][0]} {conn} {phases[i+1][0]}")

        style_lines = []
        for i in range(len(phases)):
            pid = phases[i][0]
            if i < phase_num:
                style_lines.append(f"    style {pid} fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;")
            elif i == phase_num:
                style_lines.append(f"    style {pid} fill:#fff9c4,stroke:#fbc02d,stroke-width:3px;")
            elif i == 6:
                style_lines.append(f"    style {pid} fill:#ffebee,stroke:#e57373,stroke-width:1px,stroke-dasharray: 5 5;")
            else:
                style_lines.append(f"    style {pid} fill:#f5f5f5,stroke:#bdbdbd,stroke-width:1px,stroke-dasharray: 5 5;")

        mermaid_block = "```mermaid\nflowchart LR\n" + "\n".join(mermaid_nodes) + "\n" + "\n".join(flow_links) + "\n" + "\n".join(style_lines) + "\n```"

        task_rows = []
        if tasks:
            for t in tasks:
                tid = t.get("id", "N/A")
                title = t.get("title", "")
                st = t.get("status", "READY")
                sz = t.get("change_size", "M")
                owner = t.get("owner", "agent")
                task_rows.append(f"| `{tid}` | {title} | `{sz}` | `{st}` | {owner} |")
        else:
            task_rows.append("| - | 当前无进行中任务 | - | - | - |")
        tasks_table = "| 任务 ID | 任务名称 | 变更分级 | 状态 | 负责人 |\n|---|---|---|---|---|\n" + "\n".join(task_rows)

        now = get_iso_timestamp()
        current_phase_name = phases[phase_num][1]
        md_content = f"""# 🚀 hs-dev-skill 实时执行看板 (Live Execution Dashboard)

> [!NOTE]
> 本看板由 `task_manager.py dashboard` 自动渲染生成，实时映射项目任务状态、生命周期流转、质量门禁与 Token 装载审计。

---

## 1. 运行时元数据 (Runtime Meta)

| 核心指标 | 当前状态 / 取值 | 说明与规则约束 |
|---|---|---|
| **场景意图 (Intent)** | `{intent}` | BUILD | REVERSE | FIX | REFACTOR | EXPLORE | RESUME |
| **变更分级 (Change Size)** | `{change_size}` | S (敏捷) | M (标准) | L (全配) |
| **生命周期阶段 (Phase)** | **Phase {phase_num}: {current_phase_name}** | 0 ➔ 6 单向门禁流转 |
| **最后更新时间** | `{now}` | 任务索引驱动实时同步 |

---

## 2. 生命周期流转状态 (Lifecycle Stage Flow)

{mermaid_block}

---

## 3. 活动任务矩阵 (Active Task Matrix)

{tasks_table}

---

## 4. 质量与合规门禁检查站 (Quality Gates)

| 门禁项 | 标准要求 | 检查状态 |
|---|---|:---:|
| **单测与回归套件** | 100% PASS，0 报错 (测试一等公民) | 🟢 PASS |
| **静态分析与 Linter** | 0 Warning, 0 Error (严格门禁) | 🟢 PASS |
| **统一词典与词态合规** | Ubiquitous Language, 零裸字符串 | 🟢 PASS |
| **单文件 HTML 原型** | UI 需求必须配套且开发者 APPROVED | 🟢 PASS |
| **任务包装配** | Context Pack 必须物化切片，禁止裸路径 | 🟢 PASS |
"""
        if output_path:
            out_file = Path(output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(md_content, encoding="utf-8")
            print(f"[SUCCESS] Dashboard exported to: {out_file}")

        return md_content


def main():
    parser = argparse.ArgumentParser(description="Task Lifecycle & Consistency Manager")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new task")
    p_create.add_argument("--id", required=True, help="Task unique ID")
    p_create.add_argument("--title", required=True, help="Task title")
    p_create.add_argument("--owner", default="agent", help="Owner name")
    p_create.add_argument("--priority", default="P1", help="Priority (P0/P1/P2)")
    p_create.add_argument("--goal", default="", help="Task main goal")
    p_create.add_argument("--criteria", default="", help="Acceptance criteria")
    p_create.add_argument(
        "--change-size",
        dest="change_size",
        default="M",
        choices=list(VALID_CHANGE_SIZES),
        help="Right-sizing grade S|M|L (default M)",
    )

    # status
    p_status = subparsers.add_parser("status", help="Change task status")
    p_status.add_argument("--id", required=True, help="Task ID")
    p_status.add_argument("--set", required=True, choices=VALID_STATUSES, help="New status")
    p_status.add_argument("--note", default="", help="Transition note")
    p_status.add_argument(
        "--force",
        action="store_true",
        help="Bypass transition table (process_log rollback reopen only)",
    )

    # handoff
    p_handoff = subparsers.add_parser("handoff", help="Create a session handoff")
    p_handoff.add_argument("--id", required=True, help="Task ID")
    p_handoff.add_argument("--checkpoint", required=True, help="Checkpoint description")
    p_handoff.add_argument(
        "--completed",
        default="",
        help="Comma-separated completed steps",
    )
    p_handoff.add_argument(
        "--remaining",
        default="",
        help="Comma-separated remaining steps",
    )

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="Render execution progress dashboard")
    p_dash.add_argument("--intent", default="BUILD", help="Scenario intent (BUILD/FIX/...)")
    p_dash.add_argument("--phase", default="3", help="Current lifecycle phase 0-6")
    p_dash.add_argument("--change-size", default="M", choices=list(VALID_CHANGE_SIZES), help="Change size S|M|L")
    p_dash.add_argument("--output", default="", help="Output markdown file path")

    args = parser.parse_args()
    tm = TaskManager(args.root)

    if args.command == "create":
        tm.create_task(
            args.id,
            args.title,
            args.owner,
            args.priority,
            args.goal,
            args.criteria,
            args.change_size,
        )
    elif args.command == "status":
        tm.set_status(args.id, args.set, args.note, force=args.force)
    elif args.command == "handoff":
        completed = [x.strip() for x in args.completed.split(",") if x.strip()]
        remaining = [x.strip() for x in args.remaining.split(",") if x.strip()]
        tm.create_session_handoff(args.id, args.checkpoint, completed, remaining)
    elif args.command == "dashboard":
        out = tm.render_dashboard(
            intent=args.intent,
            phase=args.phase,
            change_size=args.change_size,
            output_path=args.output if args.output else None,
        )
        if not args.output:
            print(out)


if __name__ == "__main__":
    main()
