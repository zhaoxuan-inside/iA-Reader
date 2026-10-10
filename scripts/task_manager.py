#!/usr/bin/env python3
"""
task_manager.py
任务生命周期与三文件强一致性管理器。
支持任务创建、状态机流转、自动滚动分片、任务归档与会话交接。
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from idx_manager import IdxManager

VALID_STATUSES = ["DRAFT", "READY", "IN_PROGRESS", "BLOCKED", "VERIFYING", "COMPLETED", "ABORTED"]


def get_iso_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskManager:
    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root).resolve()
        self.docs_root = self.root / "hs_dev_docs"
        self.task_root = self.docs_root / "_08_dev_process/_09_task"
        self.brief_dir = self.task_root / "_01_task_brief"
        self.detail_dir = self.task_root / "_02_task_detail"
        self.context_pack_dir = self.task_root / "_03_task_context_pack"
        self.handoff_dir = self.docs_root / "_08_dev_process/_05_session_handoff"

        self.task_idx_path = self.task_root / "_00_task.idx"
        self.archive_idx_path = self.task_root / "_00_task_archive.idx"

    def create_task(self, task_id: str, title: str, owner: str = "agent", priority: str = "P1", goal: str = "", criteria: str = ""):
        """创建新任务，原子更新 _00_task.idx、task_brief、task_detail 和 context_pack"""
        self.task_root.mkdir(parents=True, exist_ok=True)
        self.brief_dir.mkdir(parents=True, exist_ok=True)
        self.detail_dir.mkdir(parents=True, exist_ok=True)
        self.context_pack_dir.mkdir(parents=True, exist_ok=True)

        mgr = IdxManager(str(self.task_idx_path))
        if not mgr.metadata:
            mgr.init_idx("task_active", "_09_task")

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

- **任务 ID**：`{task_id}`
- **生成时间**：`{now}`
- **状态**：`{status}`

---

## 1. 需求与目标
{goal or title}

---

## 2. 精确注入设计引用
- 接口设计：`_05_interface_design/...`
- 方法设计：`_06_method_design/...`
- 数据库表：`_04_db_schema/...`
- 契约参考：`hs_dev_docs/_00_project/_13_mock_contract/...`
"""
        cp_file.write_text(cp_content, encoding="utf-8")

        # 3. 追加任务简述 (Task Brief) 并处理滚动分片 (10个任务一个分片)
        brief_ref = self._append_task_brief(task_id, title, status, priority, owner, goal, now)

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

        print(f"[SUCCESS] Created task '{task_id}' (Status: {status})")
        return {
            "task_id": task_id,
            "status": status,
            "detail_path": str(detail_file),
            "brief_ref": brief_ref,
            "context_pack_path": str(cp_file)
        }

    def _append_task_brief(self, task_id: str, title: str, status: str, priority: str, owner: str, goal: str, timestamp: str) -> str:
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

    def set_status(self, task_id: str, new_status: str, note: str = ""):
        """流转任务状态并原子同步三文件"""
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
            raise ValueError(f"Active task '{task_id}' not found in _00_task.idx")

        now = get_iso_timestamp()
        target_entry["status"] = new_status
        target_entry["updated_at"] = now

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

        print(f"[SUCCESS] Task '{task_id}' status transitioned to '{new_status}'")

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
            arch_mgr.init_idx("task_archive", "_09_task")

        target_entry["status"] = final_status
        arch_mgr.entries.append(target_entry)
        arch_mgr.save()
        print(f"[ARCHIVE] Task '{task_id}' archived into _00_task_archive.idx")

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
请继续执行任务 [{task_id}]。
当前断点：{checkpoint_desc}。
请阅读 hs_dev_docs/_08_dev_process/_09_task/_02_task_detail/_01_{task_id}/_00_task_detail.md 并在当前断点基础上继续推进。
```
"""
        handoff_file.write_text(content, encoding="utf-8")
        print(f"[SUCCESS] Created session handoff at: {handoff_file}")
        return str(handoff_file)


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

    # status
    p_status = subparsers.add_parser("status", help="Change task status")
    p_status.add_argument("--id", required=True, help="Task ID")
    p_status.add_argument("--set", required=True, choices=VALID_STATUSES, help="New status")
    p_status.add_argument("--note", default="", help="Transition note")

    # handoff
    p_handoff = subparsers.add_parser("handoff", help="Create a session handoff")
    p_handoff.add_argument("--id", required=True, help="Task ID")
    p_handoff.add_argument("--checkpoint", required=True, help="Checkpoint description")

    args = parser.parse_args()
    tm = TaskManager(args.root)

    if args.command == "create":
        tm.create_task(args.id, args.title, args.owner, args.priority, args.goal, args.criteria)
    elif args.command == "status":
        tm.set_status(args.id, args.set, args.note)
    elif args.command == "handoff":
        tm.create_session_handoff(args.id, args.checkpoint, [], [])


if __name__ == "__main__":
    main()
