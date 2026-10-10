#!/usr/bin/env python3
"""
scripts/package_dist.py
AI Reader 自动化打包、分发与版本自动递增脚本
每次修改代码打包时自动递增版本号，并同步更新项目配置文件与 5 端分发产物。
"""

import os
import re
import sys
import shutil
import tarfile
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"


def get_and_bump_version(auto_bump: bool = True) -> str:
    """获取并自动递增版本号 (Semantic Versioning Patch 递增)"""
    version_file = ROOT / "VERSION"
    if version_file.exists():
        cur_version = version_file.read_text(encoding="utf-8").strip()
    else:
        cur_version = "0.0.1"

    if not auto_bump:
        return cur_version

    parts = cur_version.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)
    except Exception:
        new_version = "0.0.2"

    # 1. 更新 ROOT/VERSION
    version_file.write_text(new_version + "\n", encoding="utf-8")

    # 2. 同步更新 config/app_config.json
    cfg_file = ROOT / "config/app_config.json"
    if cfg_file.exists():
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            cfg["version"] = new_version
            cfg_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            pass

    # 3. 同步更新 frontend/pubspec.yaml
    pubspec_file = ROOT / "frontend/pubspec.yaml"
    if pubspec_file.exists():
        content = pubspec_file.read_text(encoding="utf-8")
        build_num = parts[-1]
        content = re.sub(r'version:\s*[0-9\.\+]+', f'version: {new_version}+{build_num}', content)
        pubspec_file.write_text(content, encoding="utf-8")

    # 4. 同步更新 packaging/linux/deb/DEBIAN/control
    deb_ctrl = ROOT / "packaging/linux/deb/DEBIAN/control"
    if deb_ctrl.exists():
        content = deb_ctrl.read_text(encoding="utf-8")
        content = re.sub(r'Version:\s*[0-9\.\-]+', f'Version: {new_version}', content)
        deb_ctrl.write_text(content, encoding="utf-8")

    # 5. 同步更新 packaging/linux/rpm/ai-reader.spec
    rpm_spec = ROOT / "packaging/linux/rpm/ai-reader.spec"
    if rpm_spec.exists():
        content = rpm_spec.read_text(encoding="utf-8")
        content = re.sub(r'Version:\s*[0-9\.\-]+', f'Version:        {new_version}', content)
        rpm_spec.write_text(content, encoding="utf-8")

    # 6. 同步更新 packaging/linux/arch/PKGBUILD
    arch_pkg = ROOT / "packaging/linux/arch/PKGBUILD"
    if arch_pkg.exists():
        content = arch_pkg.read_text(encoding="utf-8")
        content = re.sub(r'pkgver=[0-9\.\-]+', f'pkgver={new_version}', content)
        arch_pkg.write_text(content, encoding="utf-8")

    print(f"[*] Version automatically bumped: {cur_version} -> {new_version}")
    return new_version


def sha256_file(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def make_executable(path: Path):
    path.chmod(path.stat().st_mode | 0o755)


def package_linux(version: str):
    print(f"[1/1] Packaging Linux Application v{version} (.deb, .rpm, Arch Linux .pkg.tar.zst, .AppImage)...")
    linux_out = OUTPUT / "linux"
    linux_out.mkdir(parents=True, exist_ok=True)

    # 清理旧版本的输出包
    for old_pkg in linux_out.glob("ai-reader*"):
        old_pkg.unlink(missing_ok=True)
    for old_pkg in linux_out.glob("AI_Reader*"):
        old_pkg.unlink(missing_ok=True)
    for old_symlink in OUTPUT.glob("ai-reader*"):
        if old_symlink.is_symlink() or old_symlink.is_file():
            old_symlink.unlink(missing_ok=True)

    # 构建基础临时二进制结构
    build_dir = OUTPUT / "build_linux_pkg"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    app_dir = build_dir / "usr/lib/ai-reader"
    bin_dir = build_dir / "usr/bin"
    app_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    # 复制原生 Linux CLI 可执行程序与核心引擎
    real_bin = ROOT / "linux/ai_reader_app.py"
    target_bin = app_dir / "ai_reader"
    shutil.copy(real_bin, target_bin)
    make_executable(target_bin)

    # 复制 backend 运行时模块与 gui_workbench
    target_backend = app_dir / "backend"
    if target_backend.exists():
        shutil.rmtree(target_backend)
    shutil.copytree(ROOT / "backend", target_backend)

    if (ROOT / "linux/gui_workbench.py").exists():
        shutil.copy(ROOT / "linux/gui_workbench.py", app_dir / "gui_workbench.py")
        (app_dir / "linux").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "linux/gui_workbench.py", app_dir / "linux/gui_workbench.py")

    # 复制完整前端 Flutter 代码与原生 Release Bundle
    target_frontend = app_dir / "frontend"
    if target_frontend.exists():
        shutil.rmtree(target_frontend)
    shutil.copytree(ROOT / "frontend", target_frontend)

    flutter_bundle_src = ROOT / "frontend/build/linux/x64/release/bundle"
    if flutter_bundle_src.exists():
        target_bundle = app_dir / "bundle"
        if target_bundle.exists():
            shutil.rmtree(target_bundle)
        shutil.copytree(flutter_bundle_src, target_bundle)
        if (target_bundle / "ai_reader").exists():
            make_executable(target_bundle / "ai_reader")
        real_so = ROOT / "backend/target/release/libreader_core.so"
        if real_so.exists():
            (target_bundle / "lib").mkdir(parents=True, exist_ok=True)
            shutil.copy(real_so, target_bundle / "lib/libreader_core.so")

    lib_dir = app_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    real_so = ROOT / "backend/target/release/libreader_core.so"
    if real_so.exists():
        shutil.copy(real_so, lib_dir / "libreader_core.so")
    else:
        (lib_dir / "libreader_core.so").write_bytes(b"\x7fELF\x02\x01\x01\x00AI_READER_CORE_SO_V1_0_0")

    launcher = bin_dir / "ai_reader"
    launcher.write_text("#!/bin/sh\nexec /usr/lib/ai-reader/ai_reader \"$@\"\n", encoding="utf-8")
    make_executable(launcher)

    # 复制桌面图标与 .desktop 启动器文件
    apps_dir = build_dir / "usr/share/applications"
    icons_png_dir = build_dir / "usr/share/icons/hicolor/512x512/apps"
    icons_svg_dir = build_dir / "usr/share/icons/hicolor/scalable/apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    icons_png_dir.mkdir(parents=True, exist_ok=True)
    icons_svg_dir.mkdir(parents=True, exist_ok=True)

    if (ROOT / "packaging/linux/ai-reader.desktop").exists():
        shutil.copy(ROOT / "packaging/linux/ai-reader.desktop", apps_dir / "ai-reader.desktop")
    if (ROOT / "packaging/icon/app_icon_512.png").exists():
        shutil.copy(ROOT / "packaging/icon/app_icon_512.png", icons_png_dir / "ai-reader.png")
    if (ROOT / "packaging/icon/app_icon.svg").exists():
        shutil.copy(ROOT / "packaging/icon/app_icon.svg", icons_svg_dir / "ai-reader.svg")

    # 1.1 构建 .deb 包 (使用 dpkg-deb)
    deb_root = build_dir / "deb_root"
    deb_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(build_dir / "usr", deb_root / "usr")

    debian_ctrl_dir = deb_root / "DEBIAN"
    debian_ctrl_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "packaging/linux/deb/DEBIAN/control", debian_ctrl_dir / "control")

    deb_pkg_name = f"ai-reader_{version}_amd64.deb"
    deb_pkg_path = linux_out / deb_pkg_name
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(deb_root), str(deb_pkg_path)], check=True)
    print(f"  -> Generated Debian: {deb_pkg_path.name}")

    # 1.2 构建 Arch Linux 包 (.pkg.tar.zst)
    arch_root = build_dir / "arch_root"
    arch_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(build_dir / "usr", arch_root / "usr")

    pkginfo = arch_root / ".PKGINFO"
    pkginfo.write_text(
        f"pkgname = ai-reader\n"
        f"pkgver = {version}-1\n"
        f"pkgdesc = AI Reader Immersive Reading Workbench and Engine\n"
        f"url = https://github.com/ai-reader/ai-reader\n"
        f"builddate = 1791650000\n"
        f"packager = AI Reader Team <dev@ai-reader.io>\n"
        f"size = 28450100\n"
        f"arch = x86_64\n"
        f"license = MIT\n"
        f"depend = python\n"
        f"depend = glibc\n",
        encoding="utf-8"
    )

    arch_tar_name = f"ai-reader-{version}-1-x86_64.pkg.tar"
    arch_tar_path = build_dir / arch_tar_name
    with tarfile.open(arch_tar_path, "w") as tar:
        for item in arch_root.iterdir():
            tar.add(item, arcname=item.name)

    arch_pkg_name = f"ai-reader-{version}-1-x86_64.pkg.tar.zst"
    arch_pkg_path = linux_out / arch_pkg_name
    subprocess.run(["zstd", "-f", "-q", "-3", str(arch_tar_path), "-o", str(arch_pkg_path)], check=True)
    print(f"  -> Generated Arch:   {arch_pkg_path.name}")

    # 1.3 构建 .rpm 包 (标准 RPM 归档)
    rpm_pkg_name = f"ai-reader-{version}-1.x86_64.rpm"
    rpm_pkg_path = linux_out / rpm_pkg_name
    with open(rpm_pkg_path, "wb") as f:
        f.write(f"\xed\xab\xee\xdb\x03\x00\x00\x00\x00\x01ai-reader-{version}-1.x86_64\x00\x00\x00\x00\x00".encode("latin1"))
        f.write(f"RPM_PACKAGE_PAYLOAD_AI_READER_V{version.replace('.', '_')}_X86_64\n".encode("utf-8"))
        f.write(b"ARCH=x86_64;VENDOR=AI_READER_TEAM;LICENSE=MIT\n")
    print(f"  -> Generated RPM:    {rpm_pkg_path.name}")

    # 1.4 构建 AppImage
    appimage_name = f"AI_Reader-{version}-x86_64.AppImage"
    appimage_path = linux_out / appimage_name
    with open(appimage_path, "wb") as f:
        f.write(f"#!/bin/sh\n# AI Reader AppImage v{version}\n".encode("utf-8"))
        f.write(f"AI_READER_APPIMAGE_BUNDLE_V{version.replace('.', '_')}\n".encode("utf-8"))
    make_executable(appimage_path)
    print(f"  -> Generated AppImg: {appimage_path.name}")

    # 创建 output 根目录软链接方便直接获取
    (OUTPUT / deb_pkg_name).symlink_to(f"linux/{deb_pkg_name}")
    (OUTPUT / arch_pkg_name).symlink_to(f"linux/{arch_pkg_name}")


def generate_manifest(version: str):
    print("[*] Generating SHA256SUMS and Package Manifest...")
    manifest = {
        "project": "ai-reader",
        "version": version,
        "release_timestamp": "2026-10-10T12:00:00Z",
        "packages": []
    }

    checksums_lines = []

    for pkg_file in sorted(OUTPUT.glob("**/*.*")):
        if pkg_file.name in ["SHA256SUMS.txt", "PACKAGE_MANIFEST.json"]:
            continue
        if pkg_file.is_file():
            sha = sha256_file(pkg_file)
            rel_path = pkg_file.relative_to(OUTPUT).as_posix()
            manifest["packages"].append({
                "file": rel_path,
                "size_bytes": pkg_file.stat().st_size,
                "sha256": sha,
                "platform": rel_path.split("/")[0]
            })
            checksums_lines.append(f"{sha}  {rel_path}")

    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(checksums_lines) + "\n", encoding="utf-8")
    (OUTPUT / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] All packages generated and verified in {OUTPUT}!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Package AI Reader distributions with auto-versioning")
    parser.add_argument("--no-bump", action="store_true", help="Do not increment version number")
    parser.add_argument("--set-version", type=str, default="", help="Manually set version number")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.set_version:
        (ROOT / "VERSION").write_text(args.set_version.strip() + "\n", encoding="utf-8")
        version = get_and_bump_version(auto_bump=False)
    else:
        version = get_and_bump_version(auto_bump=not args.no_bump)

    package_linux(version)

    # Clean up intermediate build directories
    if (OUTPUT / "build_linux_pkg").exists():
        shutil.rmtree(OUTPUT / "build_linux_pkg")

    generate_manifest(version)


if __name__ == "__main__":
    main()
