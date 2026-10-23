#!/usr/bin/env python3
"""
跨平台路径与运行时辅助（Windows / Linux / macOS）。

全局共享根目录统一为：Path.home() / ".hs-dev-skill"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


GLOBAL_DIR_NAME = ".hs-dev-skill"


def global_root() -> Path:
    """返回已解析的全局共享根目录（三端同一语义）。"""
    return Path.home() / GLOBAL_DIR_NAME


def preferences_path() -> Path:
    return global_root() / "preferences.yaml"


def tech_learning_dir() -> Path:
    return global_root() / "tech_learning"


def global_index_db_path() -> Path:
    """全局偏好/学习笔记 SQLite 索引（可重建缓存）。"""
    return global_root() / "global_index.sqlite"


def tag_synonyms_path() -> Path:
    return global_root() / "tag_synonyms.yaml"


def rule_cache_dir() -> Path:
    """远程领域规则缓存（可重建；由 rule_fetch.py 写入）。"""
    return global_root() / "rule_cache"


def platform_id() -> str:
    """规范化平台标识：windows | linux | macos | other。"""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    return "other"


def global_root_display() -> dict:
    """供文档/CLI 打印的多平台写法（resolved 为当前机绝对路径）。"""
    root = global_root()
    return {
        "platform": platform_id(),
        "resolved": str(root.resolve()) if root.exists() else str(root),
        "linux_macos": "$HOME/.hs-dev-skill/",
        "windows_cmd": "%USERPROFILE%\\.hs-dev-skill\\",
        "windows_pwsh": "$env:USERPROFILE\\.hs-dev-skill\\",
        "pathlib": 'Path.home() / ".hs-dev-skill"',
    }


def ensure_utf8_stdout() -> None:
    """尽量让 Windows 控制台打印中文不乱码（无则忽略）。"""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def which_python_hint() -> str:
    """给文档用的当前解释器提示。"""
    return sys.executable or "python3"


if __name__ == "__main__":
    ensure_utf8_stdout()
    info = global_root_display()
    print(f"platform:  {info['platform']}")
    print(f"resolved:  {info['resolved']}")
    print(f"linux/mac: {info['linux_macos']}")
    print(f"win cmd:   {info['windows_cmd']}")
    print(f"win pwsh:  {info['windows_pwsh']}")
    print(f"python:    {which_python_hint()}")
    print(f"HOME:      {os.environ.get('HOME') or os.environ.get('USERPROFILE')}")
