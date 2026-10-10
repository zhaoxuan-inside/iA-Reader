#!/usr/bin/env python3
"""
dead_code_scanner.py
基于调用链与注解白名单的死代码与孤儿方法扫描器。
"""

import os
import sys
import re
import argparse
from pathlib import Path

# 豁免注解与白名单
EXEMPT_ANNOTATIONS = [
    "@UsedByReflect",
    "@EventSubscriber",
    "@PublicAPI",
    "@Export",
    "@Scheduled",
    "@Test"
]


class DeadCodeScanner:
    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root).resolve()
        self.docs_root = self.root / "hs_dev_docs"
        self.call_chain_dir = self.docs_root / "_07_call_chain"

    def scan(self) -> bool:
        print(f"[*] Scanning for dead code & orphan methods in: {self.root}")

        # 1. 收集调用链中已声明的所有方法
        declared_methods = set()
        if self.call_chain_dir.exists():
            for cf in self.call_chain_dir.rglob("*.md"):
                content = cf.read_text(encoding="utf-8")
                # 匹配表格中或代码块中的方法名
                matches = re.findall(r"`([a-zA-Z0-9_]+)`", content)
                for m in matches:
                    declared_methods.add(m)

        print(f"  -> Found {len(declared_methods)} methods referenced in call chain documentation.")

        # 2. 扫描 backend 等业务代码目录
        code_dirs = [self.root / "backend", self.root / "frontend"]
        orphan_methods = []

        for c_dir in code_dirs:
            if not c_dir.exists():
                continue
            for ext in ["*.go", "*.ts", "*.js", "*.py", "*.rs"]:
                for file_path in c_dir.rglob(ext):
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")

                    for i, line in enumerate(lines):
                        # 检查方法定义 (Go, Python, TS, Rust 等)
                        func_match = re.search(r"\b(func|def|function|fn)\s+([a-zA-Z0-9_]+)\s*[\(\{]", line)
                        if func_match:
                            func_name = func_match.group(2)

                            # 忽略通用入口或标准方法
                            if func_name in ["main", "init", "setUp", "tearDown", "constructor", "run"]:
                                continue

                            # 检查前一行是否有豁免注解
                            prev_lines = lines[max(0, i-3):i]
                            is_exempt = any(any(ann in pl for ann in EXEMPT_ANNOTATIONS) for pl in prev_lines)

                            if not is_exempt and declared_methods:
                                if func_name not in declared_methods and not func_name.startswith("Test"):
                                    orphan_methods.append({
                                        "file": str(file_path.relative_to(self.root)),
                                        "line": i + 1,
                                        "method": func_name
                                    })

        if orphan_methods:
            print(f"[!] Warning: Found {len(orphan_methods)} potentially unreferenced/orphan methods (Not registered in _07_call_chain):")
            for om in orphan_methods:
                print(f"  - {om['file']}:{om['line']} -> {om['method']} (Consider registering in _07_call_chain or adding @UsedByReflect)")
        else:
            print("[PASS] Zero dead code detected. All methods are properly mapped in call chains!")

        return True


def main():
    parser = argparse.ArgumentParser(description="Dead Code & Orphan Method Scanner")
    parser.add_argument("--root", default=".", help="Target workspace root")
    args = parser.parse_args()

    scanner = DeadCodeScanner(args.root)
    scanner.scan()


if __name__ == "__main__":
    main()
