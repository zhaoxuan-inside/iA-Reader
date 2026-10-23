#!/usr/bin/env python3
"""
code_skeleton.py
基于 AST 与结构化特征的代码骨架提取器（Python / JS / TS / Go / Java / Rust）。
提取类、方法签名、类型注解与行号范围，将函数体折叠为省略号，实现 85%~95% Token 压缩。
"""

from __future__ import annotations

import ast
import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any


class CodeSkeletonExtractor:
    def __init__(self, max_line_len: int = 120):
        self.max_line_len = max_line_len

    def extract_file(self, file_path: Path) -> Dict[str, Any]:
        """提取单个文件的骨架信息"""
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        total_lines = len(content.splitlines())

        if ext == ".py":
            skeleton_text, symbols_count = self._extract_python_ast(content)
        elif ext in (".ts", ".js", ".tsx", ".jsx"):
            skeleton_text, symbols_count = self._extract_c_like_signatures(content, "ts")
        elif ext in (".go", ".rs", ".java", ".kt", ".cpp", ".c", ".h", ".hpp", ".cc", ".dart", ".swift"):
            skeleton_text, symbols_count = self._extract_c_like_signatures(content, ext.lstrip("."))
        else:
            # 默认行首符号扫描
            skeleton_text, symbols_count = self._extract_generic_signatures(content)

        skeleton_lines = len(skeleton_text.splitlines())
        compression = (
            (1.0 - (skeleton_lines / max(total_lines, 1))) * 100.0 if total_lines > 0 else 0.0
        )

        return {
            "path": str(file_path),
            "total_lines": total_lines,
            "skeleton_lines": skeleton_lines,
            "symbols_count": symbols_count,
            "compression_ratio": f"{compression:.1f}%",
            "skeleton": skeleton_text,
        }

    def extract_symbols_metadata(self, file_path: Path) -> List[Dict[str, Any]]:
        """提取代码中的结构化符号列表（用于 SQLite 索引库）"""
        if not file_path.is_file():
            return []
        ext = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".py":
            return self._extract_python_symbols(content, file_path)
        return self._extract_c_like_symbols(content, file_path)

    def _extract_python_symbols(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        try:
            tree = ast.parse(content)
        except Exception:
            return []

        def format_args(args: ast.arguments) -> str:
            arg_strs = []
            for a in args.args:
                anno = f": {ast.unparse(a.annotation)}" if a.annotation else ""
                arg_strs.append(f"{a.arg}{anno}")
            return ", ".join(arg_strs)

        symbols = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                doc_first = doc.strip().splitlines()[0] if doc else ""
                end_lineno = getattr(node, "end_lineno", node.lineno)
                bases_str = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
                symbols.append({
                    "name": node.name,
                    "kind": "class",
                    "file_path": str(file_path),
                    "signature": f"class {node.name}{bases_str}",
                    "start_line": node.lineno,
                    "end_line": end_lineno,
                    "docstring": doc_first,
                })
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        f_doc = ast.get_docstring(item) or ""
                        f_doc_first = f_doc.strip().splitlines()[0] if f_doc else ""
                        fn_end = getattr(item, "end_lineno", item.lineno)
                        prefix = "async def " if isinstance(item, ast.AsyncFunctionDef) else "def "
                        ret = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        arg_str = format_args(item.args)
                        symbols.append({
                            "name": f"{node.name}.{item.name}",
                            "kind": "method",
                            "file_path": str(file_path),
                            "signature": f"{prefix}{item.name}({arg_str}){ret}",
                            "start_line": item.lineno,
                            "end_line": fn_end,
                            "docstring": f_doc_first,
                        })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f_doc = ast.get_docstring(node) or ""
                f_doc_first = f_doc.strip().splitlines()[0] if f_doc else ""
                end_lineno = getattr(node, "end_lineno", node.lineno)
                prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                arg_str = format_args(node.args)
                symbols.append({
                    "name": node.name,
                    "kind": "function",
                    "file_path": str(file_path),
                    "signature": f"{prefix}{node.name}({arg_str}){ret}",
                    "start_line": node.lineno,
                    "end_line": end_lineno,
                    "docstring": f_doc_first,
                })

        return symbols

    def extract_dependencies(self, file_path: Path) -> List[Dict[str, Any]]:
        """提取代码中的方法/函数/包间调用与导入依赖（多语言支持）"""
        if not file_path.is_file():
            return []
        ext = file_path.suffix.lower()
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        if ext == ".py":
            return self._extract_python_dependencies(content, file_path)
        return self._extract_c_like_dependencies(content, file_path, ext)

    def _extract_python_dependencies(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        try:
            tree = ast.parse(content)
        except Exception:
            return []

        deps: List[Dict[str, Any]] = []
        ignored_builtins = {
            "print", "len", "range", "isinstance", "getattr", "setattr", "int", "str", "float",
            "bool", "dict", "list", "set", "tuple", "min", "max", "sum", "any", "all", "enumerate",
            "zip", "super", "open", "type", "hasattr", "issubclass", "round", "abs", "sorted",
        }

        # 1. 抓取 import 依赖
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.append({
                        "source_symbol": Path(file_path).stem,
                        "target_symbol": alias.name,
                        "dep_type": "IMPORT",
                        "source_file": str(file_path),
                    })
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    deps.append({
                        "source_symbol": Path(file_path).stem,
                        "target_symbol": f"{mod}.{alias.name}" if mod else alias.name,
                        "dep_type": "IMPORT",
                        "source_file": str(file_path),
                    })

        # 2. 抓取方法调用依赖
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls_name = node.name
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        source_symbol = f"{cls_name}.{item.name}"
                        for subnode in ast.walk(item):
                            if isinstance(subnode, ast.Call):
                                target = self._resolve_call_target(subnode)
                                if target and target != source_symbol and target not in ignored_builtins and not any(target.startswith(b + ".") for b in ignored_builtins):
                                    deps.append({
                                        "source_symbol": source_symbol,
                                        "target_symbol": target,
                                        "dep_type": "INTERNAL_CALL",
                                        "source_file": str(file_path),
                                    })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                source_symbol = node.name
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        target = self._resolve_call_target(subnode)
                        if target and target != source_symbol and target not in ignored_builtins and not any(target.startswith(b + ".") for b in ignored_builtins):
                            deps.append({
                                "source_symbol": source_symbol,
                                "target_symbol": target,
                                "dep_type": "INTERNAL_CALL",
                                "source_file": str(file_path),
                            })
        return deps

    def _extract_c_like_dependencies(self, content: str, file_path: Path, ext: str) -> List[Dict[str, Any]]:
        deps: List[Dict[str, Any]] = []
        base_name = Path(file_path).stem

        # 1. 通用导入扫描 (import / #include / require)
        import_patterns = [
            # TS/JS/Dart: import ... from '...' or import '...'
            re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"])"""),
            # JS: require('...')
            re.compile(r"""require\(['"]([^'"]+)['"]\)"""),
            # Java/Kotlin: import com.foo.bar.Baz;
            re.compile(r"""^\s*import\s+(?:static\s+)?([A-Za-z0-9_.*]+);"""),
            # Go: import "..." or import ( ... )
            re.compile(r"""^\s*(?:import\s+)?['"]([A-Za-z0-9_/.-]+)['"]"""),
            # C/C++: #include <...> or #include "..."
            re.compile(r"""#include\s+[<"]([^>"]+)[>"]"""),
        ]
        for line in content.splitlines():
            s = line.strip()
            if not s or s.startswith(("//", "/*", "*")):
                continue
            for pat in import_patterns:
                m = pat.search(s)
                if m:
                    target = next((g for g in m.groups() if g), "")
                    if target and not target.startswith("."):
                        deps.append({
                            "source_symbol": base_name,
                            "target_symbol": target,
                            "dep_type": "IMPORT",
                            "source_file": str(file_path),
                        })
                    break

        # 2. 调用扫描: Method.call() or identifier(...)
        call_pattern = re.compile(r"""\b([A-Za-z0-9_]{3,})\.([A-Za-z0-9_]{3,})\s*\(""")
        for line in content.splitlines():
            s = line.strip()
            if not s or s.startswith(("//", "/*", "*", "#", "import", "package")):
                continue
            for m in call_pattern.finditer(s):
                caller_obj, called_method = m.group(1), m.group(2)
                if caller_obj.lower() not in ("console", "math", "system", "log", "logger", "string", "json", "assert"):
                    deps.append({
                        "source_symbol": base_name,
                        "target_symbol": f"{caller_obj}.{called_method}",
                        "dep_type": "CALL",
                        "source_file": str(file_path),
                    })
        return deps

    def _resolve_call_target(self, call_node: ast.Call) -> Optional[str]:
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            val = call_node.func.value
            if isinstance(val, ast.Name):
                return f"{val.id}.{call_node.func.attr}"
            return call_node.func.attr
        return None

    def _extract_c_like_symbols(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        symbols = []
        patterns = [
            # Dart / Flutter: class X extends Y, Widget build, mixin, extension
            (re.compile(r"^\s*class\s+([A-Za-z0-9_]+)"), "class"),
            (re.compile(r"^\s*(?:@override\s+)?(?:Widget|Future<[^>]+>|void|[A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*\("), "method"),
            (re.compile(r"^\s*mixin\s+([A-Za-z0-9_]+)"), "type"),
            (re.compile(r"^\s*extension\s+([A-Za-z0-9_]+)"), "type"),
            # TS/JS: export class / interface / type / function / const fn = () =>
            (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:class|interface|type|enum)\s+([A-Za-z0-9_]+)"), "type"),
            (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)"), "function"),
            (re.compile(r"^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\("), "function"),
            # Go: func (r *Recv) Method(...) / func Func(...) / type Struct
            (re.compile(r"^\s*func\s+\((?:[^\)]+)\)\s+([A-Za-z0-9_]+)\s*\("), "method"),
            (re.compile(r"^\s*func\s+([A-Za-z0-9_]+)\s*\("), "function"),
            (re.compile(r"^\s*type\s+([A-Za-z0-9_]+)\s+(?:struct|interface)"), "type"),
            # Java / Kotlin: public/protected/private class/interface/enum/record
            (re.compile(r"^\s*(?:public|protected|private)?\s*(?:static\s+)?(?:abstract\s+)?(?:class|interface|enum|record)\s+([A-Za-z0-9_]+)"), "type"),
            (re.compile(r"^\s*(?:@\w+\s+)*(?:public|protected|private)?\s*(?:static\s+)?(?:final\s+)?(?:[A-Za-z0-9_<>\[\]]+\s+)+([A-Za-z0-9_]+)\s*\([^;]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{?"), "method"),
            (re.compile(r"^\s*fun\s+([A-Za-z0-9_]+)\s*\("), "function"),
            # C / C++: namespace / template class / class / struct / return_type Func(...)
            (re.compile(r"^\s*namespace\s+([A-Za-z0-9_:]+)"), "namespace"),
            (re.compile(r"^\s*(?:template\s*<[^>]*>\s*)?(?:class|struct)\s+([A-Za-z0-9_]+)"), "type"),
            (re.compile(r"^\s*(?:virtual\s+)?(?:static\s+)?(?:inline\s+)?(?:[A-Za-z0-9_:*&<>]+\s+)+([A-Za-z0-9_:]+)\s*\([^;]*\)\s*(?:const)?\s*(?:override)?\s*\{?"), "function"),
            # Rust: pub fn / pub struct / enum / trait / impl
            (re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)"), "function"),
            (re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait|impl)\s+([A-Za-z0-9_]+)"), "type"),
        ]
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "#")):
                continue
            for pat, kind in patterns:
                m = pat.search(line)
                if m:
                    # 第一捕获组即为符号名称
                    name = m.group(1).strip()
                    if not name or name.lower() in ("if", "for", "while", "switch", "catch", "return"):
                        continue
                    clean_sig = re.sub(r"\{.*$", "", stripped).strip()
                    symbols.append({
                        "name": name,
                        "kind": kind,
                        "file_path": str(file_path),
                        "signature": clean_sig,
                        "start_line": i,
                        "end_line": i,
                        "docstring": "",
                    })
                    break
        return symbols

    def _extract_python_ast(self, content: str) -> tuple[str, int]:
        """使用标准库 ast 进行高保真提取"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._extract_generic_signatures(content)

        lines: List[str] = []
        symbols_count = 0

        # 模块 Docstring
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            doc_first_line = mod_doc.strip().splitlines()[0]
            lines.append(f'"""{doc_first_line}"""\n')

        def format_args(args: ast.arguments) -> str:
            arg_strs = []
            for a in args.args:
                anno = f": {ast.unparse(a.annotation)}" if a.annotation else ""
                arg_strs.append(f"{a.arg}{anno}")
            if args.vararg:
                anno = f": {ast.unparse(args.vararg.annotation)}" if args.vararg.annotation else ""
                arg_strs.append(f"*{args.vararg.arg}{anno}")
            if args.kwarg:
                anno = f": {ast.unparse(args.kwarg.annotation)}" if args.kwarg.annotation else ""
                arg_strs.append(f"**{args.kwarg.arg}{anno}")
            return ", ".join(arg_strs)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols_count += 1
                bases_str = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
                end_lineno = getattr(node, "end_lineno", node.lineno)
                lines.append(f"[L{node.lineno}-L{end_lineno}] class {node.name}{bases_str}:")
                
                doc = ast.get_docstring(node)
                if doc:
                    lines.append(f'    """{doc.strip().splitlines()[0]}"""')

                # 类内方法与属性
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols_count += 1
                        prefix = "async def " if isinstance(item, ast.AsyncFunctionDef) else "def "
                        ret = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        fn_end = getattr(item, "end_lineno", item.lineno)
                        arg_str = format_args(item.args)
                        lines.append(f"    [L{item.lineno}-L{fn_end}] {prefix}{item.name}({arg_str}){ret}: ...")
                    elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        lines.append(f"    [L{item.lineno}] {item.target.id}: {ast.unparse(item.annotation)}")

                lines.append("")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols_count += 1
                prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                end_lineno = getattr(node, "end_lineno", node.lineno)
                arg_str = format_args(node.args)
                lines.append(f"[L{node.lineno}-L{end_lineno}] {prefix}{node.name}({arg_str}){ret}: ...")

            elif isinstance(node, ast.Assign):
                # 提取全局常量或顶级声明
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        lines.append(f"[L{node.lineno}] {target.id} = ...")

        return "\n".join(lines).strip(), symbols_count

    def _extract_c_like_signatures(self, content: str, lang: str) -> tuple[str, int]:
        """针对 TS/JS/Go/Java/C/C++/Rust/Flutter 使用高级正则提取"""
        lines = content.splitlines()
        skeleton_lines = []
        symbols_count = 0

        patterns = [
            # Dart / Flutter
            re.compile(r"^\s*class\s+([A-Za-z0-9_]+)(?:\s+extends\s+[A-Za-z0-9_<>]+)?"),
            re.compile(r"^\s*(?:@override\s+)?(?:Widget|Future<[^>]+>|void|[A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*\("),
            re.compile(r"^\s*(?:mixin|extension)\s+([A-Za-z0-9_]+)"),
            # TS/JS
            re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(class|interface|type|enum)\s+([A-Za-z0-9_]+)"),
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\("),
            re.compile(r"^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\("),
            # Go
            re.compile(r"^\s*func\s+\((?:[^\)]+)\)\s+([A-Za-z0-9_]+)\s*\("),
            re.compile(r"^\s*func\s+([A-Za-z0-9_]+)\s*\("),
            re.compile(r"^\s*type\s+([A-Za-z0-9_]+)\s+(struct|interface)"),
            # Java / Kotlin
            re.compile(r"^\s*(?:public|protected|private)?\s*(?:static\s+)?(?:abstract\s+)?(class|interface|enum|record)\s+([A-Za-z0-9_]+)"),
            re.compile(r"^\s*(?:@\w+\s+)*(?:public|protected|private)?\s*(?:static\s+)?(?:final\s+)?(?:[A-Za-z0-9_<>\[\]]+\s+)+([A-Za-z0-9_]+)\s*\("),
            re.compile(r"^\s*fun\s+([A-Za-z0-9_]+)\s*\("),
            # C / C++
            re.compile(r"^\s*namespace\s+([A-Za-z0-9_:]+)"),
            re.compile(r"^\s*(?:template\s*<[^>]*>\s*)?(?:class|struct)\s+([A-Za-z0-9_]+)"),
            re.compile(r"^\s*(?:virtual\s+)?(?:static\s+)?(?:[A-Za-z0-9_:*&<>]+\s+)+([A-Za-z0-9_:]+)\s*\("),
            # Rust
            re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)"),
            re.compile(r"^\s*(?:pub\s+)?(struct|enum|trait|impl)\s+([A-Za-z0-9_]+)"),
        ]

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "#")):
                continue

            for pat in patterns:
                if pat.search(line):
                    symbols_count += 1
                    clean_sig = re.sub(r"\{.*$", "{ ... }", stripped)
                    if not clean_sig.endswith(("{ ... }", ";", ":")):
                        clean_sig += " { ... }"
                    skeleton_lines.append(f"[L{i}] {clean_sig}")
                    break

        return "\n".join(skeleton_lines), symbols_count

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "#")):
                continue

            for pat in patterns:
                if pat.search(line):
                    symbols_count += 1
                    # 截取签名行
                    clean_sig = re.sub(r"\{.*$", "{ ... }", stripped)
                    if not clean_sig.endswith(("{ ... }", ";", ":")):
                        clean_sig += " { ... }"
                    skeleton_lines.append(f"[L{i}] {clean_sig}")
                    break

        return "\n".join(skeleton_lines), symbols_count

    def _extract_generic_signatures(self, content: str) -> tuple[str, int]:
        lines = content.splitlines()
        res = []
        symbols = 0
        for i, line in enumerate(lines, start=1):
            if re.match(r"^[A-Za-z_#]", line) and len(line.strip()) > 3:
                symbols += 1
                res.append(f"[L{i}] {line.strip()[:100]}")
        return "\n".join(res), symbols

    def scan_directory(
        self,
        dir_path: Path,
        extensions: Optional[List[str]] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """递归扫描目录并提取骨架清单"""
        if not extensions:
            extensions = [".py", ".ts", ".js", ".go", ".rs", ".java"]

        results = []
        dir_path = dir_path.resolve()

        for root, dirs, files in os.walk(dir_path):
            # 过滤隐藏目录和构建目录
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ("node_modules", "vendor", "output", "__pycache__", "dist", "build")
            ]
            rel_depth = len(Path(root).relative_to(dir_path).parts)
            if rel_depth > max_depth:
                continue

            for f in sorted(files):
                f_path = Path(root) / f
                if f_path.suffix.lower() in extensions:
                    try:
                        res = self.extract_file(f_path)
                        results.append(res)
                    except Exception as e:
                        pass

        return results


def main():
    parser = argparse.ArgumentParser(description="AST & Signature Code Skeleton Extractor")
    parser.add_argument("--path", required=True, help="File or directory path to extract skeleton from")
    parser.add_argument("--format", default="text", choices=["text", "md", "json"], help="Output format")
    parser.add_argument("--depth", type=int, default=3, help="Max recursion depth for directories")
    args = parser.parse_args()

    extractor = CodeSkeletonExtractor()
    target = Path(args.path).resolve()

    if target.is_file():
        data = extractor.extract_file(target)
        if args.format == "json":
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False))
        elif args.format == "md":
            print(f"### 📄 骨架投影：`{target.name}` (行数: {data['total_lines']} ➔ {data['skeleton_lines']} | 压缩率: {data['compression_ratio']})\n")
            print("```text\n" + data["skeleton"] + "\n```")
        else:
            print(f"[*] Skeleton for: {target} ({data['total_lines']}L -> {data['skeleton_lines']}L, saved {data['compression_ratio']})")
            print("-" * 60)
            print(data["skeleton"])

    elif target.is_dir():
        results = extractor.scan_directory(target, max_depth=args.depth)
        total_orig = sum(r["total_lines"] for r in results)
        total_skel = sum(r["skeleton_lines"] for r in results)
        total_comp = (1.0 - (total_skel / max(total_orig, 1))) * 100.0 if total_orig > 0 else 0.0

        if args.format == "json":
            import json
            print(json.dumps({"summary": {"files": len(results), "original_lines": total_orig, "skeleton_lines": total_skel, "compression": f"{total_comp:.1f}%"}, "files": results}, indent=2, ensure_ascii=False))
        else:
            print(f"[*] Repository Skeleton Summary: {len(results)} files, {total_orig} lines -> {total_skel} lines (Saved {total_comp:.1f}% tokens)")
            print("=" * 70)
            for r in results:
                rel_path = os.path.relpath(r["path"], str(target))
                print(f"\n[File: {rel_path}] ({r['total_lines']}L -> {r['skeleton_lines']}L, -{r['compression_ratio']})")
                print("-" * 50)
                print(r["skeleton"])


if __name__ == "__main__":
    main()
