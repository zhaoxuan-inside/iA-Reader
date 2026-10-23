#!/usr/bin/env python3
"""
fake_code_scanner.py
假代码 / 占位符扫描器（完成度闭环门禁，协议见 references/completion_audit.md）。
扫描业务代码目录：占位注释、空桩函数体、NotImplemented 桩、跳过/掏空的测试、
业务代码 Mock 分支、空 catch、空断言。
命中默认 exit 1（阻断）；行内 `hs-allow: <理由>` 可豁免该行；--warn-only 降级为告警。
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ALLOW_MARKER = "hs-allow"

# 业务代码常见目录（含 test：被跳过的测试正是「假绿」的主要来源）
DEFAULT_CODE_DIRS = [
    "backend", "frontend", "src", "app", "server", "api", "services",
    "web", "mobile", "desktop", "internal", "cmd", "pkg",
    "scripts", "test", "tests", "e2e",
]

# 目录名级排除：依赖产物、快照/夹具数据、合法的 mock 伪数据之家（mock_contract_guide.md）
DEFAULT_EXCLUDES = {
    "node_modules", "dist", "build", "vendor", "__pycache__", "target",
    ".next", ".nuxt", "coverage", "__snapshots__", "fixtures", "testdata",
    "mock", ".git",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".go", ".java", ".kt", ".rs", ".php", ".rb", ".cs", ".swift",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".sh",
}

# (类别, 行级规则)。类别与 references/completion_audit.md §1 黑名单一一对应。
LINE_RULES = [
    ("marker-todo", re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b")),  # hs-allow: 扫描器自身规则定义
    # 中文占位须锚定注释符，避免误伤「未实现清单」等合法业务措辞
    ("marker-todo", re.compile(r"(?:#|//|/\*|<!--)\s*(?:待实现|待补充|占位实现|暂未实现|尚未实现|未实现[:：])")),  # hs-allow: 扫描器自身规则定义
    ("stub-not-implemented", re.compile(r"\braise\s+NotImplementedError\b")),
    ("stub-not-implemented", re.compile(r"\bNotImplementedException\b")),  # hs-allow: 扫描器自身规则定义
    ("stub-not-implemented", re.compile(
        r"\bthrow new\s+\w*(?:Error|Exception)\s*\(\s*[\"'][^\"']*not implemented", re.IGNORECASE)),
    ("stub-not-implemented", re.compile(r"\bpanic\s*\(\s*[\"'][^\"']*not implemented", re.IGNORECASE)),
    ("test-skipped", re.compile(r"^\s*(?:xdescribe|xit)\s*\(")),
    ("test-skipped", re.compile(r"\b(?:it|test|describe)\.skip\s*\(")),
    ("test-skipped", re.compile(r"\bit\.todo\s*\(")),
    ("test-skipped", re.compile(r"@pytest\.mark\.skip\w*|@unittest\.skip\w*|pytest\.skip\s*\(|self\.skipTest\s*\(")),
    ("test-skipped", re.compile(r"\bt\.Skip\s*\(")),
    ("empty-catch", re.compile(r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}")),
    ("assert-true", re.compile(
        r"\bassert\s+True\b|\bassertTrue\s*\(\s*True\s*\)|\bexpect\s*\(\s*true\s*\)\s*\.\s*toBe\s*\(\s*true\s*\)")),
    ("mock-branch", re.compile(
        r"\bif\b[^\n]*\b(?:isMock|is_mock|useMock|use_mock|mockEnabled|mock_enabled|MOCK_MODE|VITE_USE_MOCK)\b")),
]

CATEGORY_HINTS = {
    "marker-todo": "占位注释：实现它，或 BLOCKED 并列入未完成清单（禁止留注释冒充完成）",
    "stub-not-implemented": "NotImplemented 桩：补真实逻辑；真实 SPI/接口桩须行内 hs-allow: 理由",
    "stub-empty-body": "空桩函数体：补真实逻辑；真实 SPI/接口桩须行内 hs-allow: 理由",
    "test-skipped": "跳过的测试：门禁视 skip 为失败；写真实断言或删除该用例",
    "empty-catch": "空 catch 吞异常：处理、记日志或重抛",
    "assert-true": "空断言：写真实断言",
    "mock-branch": "业务代码 Mock 分支：改走 mock/ Sidecar + Test Profile（mock_contract_guide.md）",
}

STUB_EXEMPT_DECORATORS = {"overload", "abstractmethod", "typing.overload", "abc.abstractmethod"}


def _dotted(node):
    """AST 节点 → 点分名称字符串（兼容 py3.8，无 ast.unparse 依赖）"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _dotted(node.func)
    return ""


def _is_const_stmt(stmt, value):
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is value
    )


def _raises_not_implemented(stmt):
    if not isinstance(stmt, ast.Raise) or stmt.exc is None:
        return False
    name = _dotted(stmt.exc)
    return name.endswith("NotImplementedError")


def _is_stub_body(body):
    """去掉 docstring 后只剩 pass / ... / NotImplemented 抛出 → 空桩"""
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return True  # 仅 docstring，同样没有实现
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if _is_const_stmt(stmt, ...):
            continue
        if _raises_not_implemented(stmt):
            continue
        return False
    return True


def _is_empty_handler(handler):
    """except: pass 形态的空捕获；显式捕获 NotImplemented 的空处理属合法控制流，放行"""
    if handler.type is not None and "NotImplementedError" in ast.dump(handler.type):
        return False
    body = handler.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return True
    return all(isinstance(s, ast.Pass) or _is_const_stmt(s, ...) for s in body)


class _PyStubVisitor(ast.NodeVisitor):
    """Python AST 级空桩检测（比行级正则更稳，避免误报多行体）"""

    def __init__(self, rel_path, lines, add_finding):
        self.rel_path = rel_path
        self.lines = lines
        self.add_finding = add_finding
        self.class_bases = []

    def _line_allowed(self, lineno):
        return 0 < lineno <= len(self.lines) and ALLOW_MARKER in self.lines[lineno - 1]

    def _line_text(self, lineno):
        if 0 < lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_ClassDef(self, node):
        self.class_bases.append(" ".join(_dotted(b) for b in node.bases))
        self.generic_visit(node)
        self.class_bases.pop()

    def visit_FunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _check_function(self, node):
        for dec in node.decorator_list:
            name = _dotted(dec)
            if name in STUB_EXEMPT_DECORATORS or name.split(".")[-1] in STUB_EXEMPT_DECORATORS:
                return
        # Protocol / ABC 中的 `...` 方法体是合法接口定义
        if self.class_bases:
            for bases in self.class_bases:
                if "Protocol" in bases or bases.endswith(" ABC") or bases == "ABC":
                    return
        if _is_stub_body(node.body):
            body_line = node.body[0].lineno if node.body else node.lineno
            if not self._line_allowed(node.lineno) and not self._line_allowed(body_line):
                self.add_finding(self.rel_path, node.lineno, "stub-empty-body",
                                 self._line_text(node.lineno))

    def visit_ExceptHandler(self, node):
        if _is_empty_handler(node) and not self._line_allowed(node.lineno):
            self.add_finding(self.rel_path, node.lineno, "empty-catch",
                             self._line_text(node.lineno))
        self.generic_visit(node)


class FakeCodeScanner:
    def __init__(self, workspace_root, code_dirs=None, excludes=None):
        self.root = Path(workspace_root).resolve()
        self.code_dirs = list(code_dirs) if code_dirs else list(DEFAULT_CODE_DIRS)
        self.excludes = set(excludes) if excludes is not None else set(DEFAULT_EXCLUDES)
        self.findings = []

    def scan(self):
        self.findings = []
        seen = set()
        for name in self.code_dirs:
            target = self.root / name
            if not target.is_dir():
                continue
            for file_path in sorted(target.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in CODE_EXTENSIONS:
                    continue
                rel_parts = file_path.relative_to(self.root).parts[:-1]
                if any(part in self.excludes for part in rel_parts):
                    continue
                for finding in self._scan_file(file_path):
                    key = (finding["path"], finding["line"], finding["category"])
                    if key not in seen:
                        seen.add(key)
                        self.findings.append(finding)
        return self.findings

    def _add(self, rel_path, line, category, snippet):
        return {
            "path": rel_path,
            "line": line,
            "category": category,
            "snippet": snippet[:160],
        }

    def _scan_file(self, file_path):
        results = []
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return results
        rel = str(file_path.relative_to(self.root)).replace("\\", "/")
        lines = text.splitlines()

        for idx, line in enumerate(lines, 1):
            if ALLOW_MARKER in line:
                continue
            hit_categories = set()
            for category, rule in LINE_RULES:
                if category in hit_categories:
                    continue
                if rule.search(line):
                    hit_categories.add(category)
                    results.append(self._add(rel, idx, category, line.strip()))

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                return results
            _PyStubVisitor(rel, lines, lambda p, l, c, s: results.append(self._add(p, l, c, s))).visit(tree)

        return results


def scan_root(workspace_root, code_dirs=None):
    """供 verify_consistency 等门禁脚本复用的模块级入口"""
    return FakeCodeScanner(workspace_root, code_dirs=code_dirs).scan()


def main():
    parser = argparse.ArgumentParser(
        description="假代码 / 占位符扫描器（完成度闭环门禁，见 references/completion_audit.md）")
    parser.add_argument("--root", default=".", help="目标工作区根目录")
    parser.add_argument("--code-dirs", default="",
                        help="逗号分隔的业务代码目录，覆盖默认目录表")
    parser.add_argument("--warn-only", action="store_true",
                        help="命中时仅告警不阻断（exit 0）")
    args = parser.parse_args()

    code_dirs = [s.strip() for s in args.code_dirs.split(",") if s.strip()] or None
    scanner = FakeCodeScanner(args.root, code_dirs=code_dirs)
    scanned = [d for d in scanner.code_dirs if (scanner.root / d).is_dir()]
    print(f"[*] Scanning fake code / placeholders at: {scanner.root} (dirs: {', '.join(scanned) or 'none'})")

    findings = scanner.scan()
    if not findings:
        print("[PASS] No fake code / placeholders detected in business code directories.")
        return 0

    print(f"[FAIL] Fake code / placeholder scan found {len(findings)} issue(s):")
    for f in findings:
        print(f"  [{f['category']}] {f['path']}:{f['line']}: {f['snippet']}")
        print(f"      -> {CATEGORY_HINTS.get(f['category'], '')}")
    print("  豁免纪律：行内 `hs-allow: <理由>` 仅限真实 SPI/接口桩；协议见 references/completion_audit.md")
    if args.warn_only:
        print("[WARN] --warn-only：降级为告警，本轮不阻断。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
