#!/usr/bin/env python3
"""
idx_manager.py
JSONL 格式 .idx 索引文件管理器，支持创建、追加、更新、校验、防漂移检测（Digest）与重索引。
"""

import os
import sys
import json
import hashlib
import argparse
from typing import List, Dict, Any, Optional, Tuple


def calculate_digest(file_path: str) -> Optional[str]:
    """计算文件的 SHA-256 哈希前 8 位"""
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        return h[:8]
    except Exception:
        return None


class IdxManager:
    def __init__(self, idx_file_path: str):
        self.idx_file_path = os.path.abspath(idx_file_path)
        self.dir_path = os.path.dirname(self.idx_file_path)
        self.metadata: Dict[str, Any] = {}
        self.entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """加载并解析 JSONL 索引文件"""
        if not os.path.exists(self.idx_file_path):
            return

        with open(self.idx_file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            return

        try:
            self.metadata = json.loads(lines[0])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid metadata line in {self.idx_file_path}: {e}")

        self.entries = []
        for i, line in enumerate(lines[1:], start=2):
            try:
                entry = json.loads(line)
                self.entries.append(entry)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {i} in {self.idx_file_path}: {e}")

    def save(self):
        """保存索引回 JSONL 文件"""
        os.makedirs(self.dir_path, exist_ok=True)
        with open(self.idx_file_path, "w", encoding="utf-8") as f:
            # 写入首行元数据
            f.write(json.dumps(self.metadata, ensure_ascii=False) + "\n")
            # 写入索引条目
            for entry in self.entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def init_idx(self, category: str, root: str, version: str = "1.0"):
        """初始化空的索引文件"""
        self.metadata = {
            "version": version,
            "category": category,
            "root": root
        }
        self.entries = []
        self.save()

    def add_entry(self, entry_id: str, title: str, rel_path: str, status: str = "active", auto_digest: bool = True) -> Dict[str, Any]:
        """追加或更新单个索引条目"""
        # 计算相对文件对应的绝对路径以生成 digest
        target_abs_path = os.path.join(self.dir_path, rel_path)
        digest = calculate_digest(target_abs_path) if auto_digest else None

        entry = {
            "id": entry_id,
            "title": title,
            "path": rel_path,
            "status": status
        }
        if digest:
            entry["digest"] = digest

        # 检查是否已存在相同 ID
        for i, existing in enumerate(self.entries):
            if existing.get("id") == entry_id:
                self.entries[i] = entry
                self.save()
                return entry

        # 不存在则直接追加
        self.entries.append(entry)
        self.save()
        return entry

    def remove_entry(self, entry_id: str) -> bool:
        """删除指定 ID 的条目"""
        original_len = len(self.entries)
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        if len(self.entries) != original_len:
            self.save()
            return True
        return False

    def update_digest(self) -> int:
        """更新所有条目的内容哈希"""
        updated_count = 0
        for entry in self.entries:
            rel_path = entry.get("path")
            if rel_path:
                target_abs_path = os.path.join(self.dir_path, rel_path)
                new_digest = calculate_digest(target_abs_path)
                if new_digest and entry.get("digest") != new_digest:
                    entry["digest"] = new_digest
                    updated_count += 1
        if updated_count > 0:
            self.save()
        return updated_count

    def verify(self) -> Tuple[bool, List[str]]:
        """校验索引文件与磁盘文件的一致性与哈希防漂移"""
        errors = []
        if not self.metadata:
            errors.append(f"Missing metadata header in {self.idx_file_path}")
            return False, errors

        seen_ids = set()
        for idx, entry in enumerate(self.entries, start=2):
            entry_id = entry.get("id")
            if not entry_id:
                errors.append(f"Line {idx}: missing 'id'")
                continue
            if entry_id in seen_ids:
                errors.append(f"Line {idx}: duplicate id '{entry_id}'")
            seen_ids.add(entry_id)

            rel_path = entry.get("path")
            if not rel_path:
                errors.append(f"Line {idx} ({entry_id}): missing 'path'")
                continue

            target_abs_path = os.path.join(self.dir_path, rel_path)
            if not os.path.exists(target_abs_path):
                errors.append(f"Line {idx} ({entry_id}): target file not found '{rel_path}'")
                continue

            expected_digest = entry.get("digest")
            if expected_digest:
                actual_digest = calculate_digest(target_abs_path)
                if actual_digest and actual_digest != expected_digest:
                    errors.append(f"Line {idx} ({entry_id}): digest mismatch for '{rel_path}' (expected {expected_digest}, got {actual_digest})")

        return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="JSONL .idx Index Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new .idx file")
    p_init.add_argument("idx_path", help="Path to .idx file")
    p_init.add_argument("--category", required=True, help="Category name")
    p_init.add_argument("--root", required=True, help="Root folder name")

    # add
    p_add = subparsers.add_parser("add", help="Add or update an index entry")
    p_add.add_argument("idx_path", help="Path to .idx file")
    p_add.add_argument("--id", required=True, help="Entry unique ID")
    p_add.add_argument("--title", required=True, help="Entry title")
    p_add.add_argument("--path", required=True, help="Relative path to target file")
    p_add.add_argument("--status", default="active", help="Status (active/archived/draft)")

    # verify
    p_ver = subparsers.add_parser("verify", help="Verify .idx file consistency and digests")
    p_ver.add_argument("idx_path", help="Path to .idx file")

    # update-digest
    p_upd = subparsers.add_parser("update-digest", help="Update all digests in .idx file")
    p_upd.add_argument("idx_path", help="Path to .idx file")

    args = parser.parse_args()

    if args.command == "init":
        mgr = IdxManager(args.idx_path)
        mgr.init_idx(args.category, args.root)
        print(f"[SUCCESS] Initialized .idx at {args.idx_path}")

    elif args.command == "add":
        mgr = IdxManager(args.idx_path)
        entry = mgr.add_entry(args.id, args.title, args.path, args.status)
        print(f"[SUCCESS] Added entry '{args.id}': {entry}")

    elif args.command == "verify":
        mgr = IdxManager(args.idx_path)
        valid, errors = mgr.verify()
        if valid:
            print(f"[PASS] {args.idx_path} is fully valid ({len(mgr.entries)} entries).")
            sys.exit(0)
        else:
            print(f"[FAIL] {args.idx_path} verification failed:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    elif args.command == "update-digest":
        mgr = IdxManager(args.idx_path)
        count = mgr.update_digest()
        print(f"[SUCCESS] Updated {count} digests in {args.idx_path}")


if __name__ == "__main__":
    main()
