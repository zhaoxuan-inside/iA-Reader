#!/usr/bin/env python3
"""
log_filter.py
命令行与测试输出降噪过滤器。
截断冗余执行日志、折叠成功用例，仅保留失败用例、关键断言与摘要，减少 80%+ 控制台上下文噪音。
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
import argparse
from typing import List, Tuple


class LogFilter:
    def __init__(self, max_error_lines: int = 25):
        self.max_error_lines = max_error_lines

    def filter_text(self, text: str, returncode: int = 0) -> str:
        """过滤并提炼测试或构建日志"""
        lines = text.splitlines()
        total_lines = len(lines)
        if total_lines <= 10:
            return text

        # 检查是否全部成功 (returncode == 0 且存在 OK / PASSED / 100% 绿标志)
        last_non_empty = [l.strip() for l in lines if l.strip()][-3:]
        ends_with_ok = any(l == "OK" or "PASSED" in l for l in last_non_empty)

        if returncode == 0 and ends_with_ok:
            summary_parts = []
            for line in lines:
                if re.search(r"(Ran \d+ tests in|passed in|\bOK\b|checks passed|SUCCESS)", line, re.I):
                    summary_parts.append(line.strip())
            # 提炼去重
            clean_parts = list(dict.fromkeys(summary_parts))
            summary_str = " | ".join(clean_parts[-3:]) if clean_parts else "All tests passed (Zero errors)"
            return f"[FILTERED PASS] {summary_str} (Original {total_lines} lines suppressed, 95%+ noise eliminated)."

        # 如果有失败，提炼失败块
        filtered_lines: List[str] = []
        capture_failure = False
        failure_count = 0

        for line in lines:
            stripped = line.strip()

            # 命中关键错误头
            if any(k in line for k in ("FAIL:", "ERROR:", "[FAIL]", "FAILED", "AssertionError", "SyntaxError")):
                capture_failure = True
                failure_count += 1
                filtered_lines.append(line)
                continue

            # 命中分割线或摘要行
            if any(k in stripped for k in ("===", "---", "Ran ", "FAILED (")):
                filtered_lines.append(line)
                capture_failure = False
                continue

            # 在失败块内部，过滤掉框架内部文件栈 (如 unittest/case.py 等)
            if capture_failure:
                if "unittest/case.py" in line or "pytest" in line and "site-packages" in line:
                    continue
                if len(filtered_lines) < self.max_error_lines * failure_count:
                    filtered_lines.append(line)

        if filtered_lines:
            header = f"[FILTERED FAILURE] Captured {failure_count} failure events from {total_lines} lines:\n"
            return header + "\n".join(filtered_lines)

        # 兜底：保留头尾
        head = lines[:10]
        tail = lines[-10:]
        return "\n".join(head) + f"\n\n... [{total_lines - 20} lines suppressed for brevity] ...\n\n" + "\n".join(tail)

    def run_command(self, command: str) -> int:
        """执行命令并实时过滤输出"""
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, _ = proc.communicate()
        filtered = self.filter_text(stdout, returncode=proc.returncode)
        print(filtered)
        return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="Command Log Noise Filter & Truncator")
    parser.add_argument("--cmd", help="Command to run and filter output from")
    parser.add_argument("--max-lines", type=int, default=25, help="Max failure detail lines")
    args = parser.parse_args()

    lf = LogFilter(max_error_lines=args.max_lines)

    if args.cmd:
        code = lf.run_command(args.cmd)
        sys.exit(code)
    else:
        # Read from stdin
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            print(lf.filter_text(content))
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
