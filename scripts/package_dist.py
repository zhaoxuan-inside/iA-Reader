#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/package_dist.py — 发布产物清单生成器

单一打包事实源是 scripts/build_linux_deb.sh（launcher 架构、本地盘 staging、
真实工具链产物）；本脚本只负责：执行该脚本 → 对真实存在的产物生成
SHA256SUMS.txt 与 PACKAGE_MANIFEST.json（真实尺寸/时间戳，逐文件校验和）。

历史版本曾在此脚本内直接伪造产物（缺失 .so 时写字节桩、写 RPM/AppImage
占位文件、硬编码发布时间戳）——全部移除；rpm/arch/appimage 需真实
rpmbuild/makepkg/appimage 工具链，待具备后经独立构建脚本接入。
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
LINUX_OUT = OUTPUT / "linux"
BUILD_SCRIPT = ROOT / "scripts" / "build_linux_deb.sh"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def generate_manifest(version: str):
    print("[*] Generating SHA256SUMS and Package Manifest...")
    manifest = {
        "project": "ai-reader",
        "version": version,
        "release_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "packages": [],
    }
    checksums_lines = []

    # 只登记真实产物文件；排除清单自身；平台按产物目录归因
    platform_by_dir = {"linux": "linux-x64", "android": "android"}
    for sub_dir, platform in platform_by_dir.items():
        out_dir = OUTPUT / sub_dir
        if not out_dir.is_dir():
            continue
        for pkg_file in sorted(out_dir.glob("*")):
            if pkg_file.name in ("SHA256SUMS.txt", "PACKAGE_MANIFEST.json"):
                continue
            if not pkg_file.is_file():
                continue
            sha = sha256_file(pkg_file)
            rel_path = pkg_file.relative_to(OUTPUT).as_posix()
            manifest["packages"].append(
                {
                    "file": rel_path,
                    "size_bytes": pkg_file.stat().st_size,
                    "sha256": sha,
                    "platform": platform,
                }
            )
            checksums_lines.append(f"{sha}  {rel_path}")

    (OUTPUT / "SHA256SUMS.txt").write_text(
        "\n".join(checksums_lines) + "\n", encoding="utf-8"
    )
    (OUTPUT / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[SUCCESS] Manifest generated for {len(manifest['packages'])} package(s) in {OUTPUT}")


def main():
    parser = argparse.ArgumentParser(
        description="Build (via build_linux_deb.sh) and generate verified dist manifest"
    )
    parser.add_argument(
        "--manifest-only", action="store_true",
        help="跳过构建，仅对现有产物重新生成清单",
    )
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if not args.manifest_only:
        print("[*] Running single-source packaging script: build_linux_deb.sh")
        subprocess.run(["bash", str(BUILD_SCRIPT)], check=True)

    generate_manifest(get_version())


if __name__ == "__main__":
    main()
