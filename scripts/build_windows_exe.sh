#!/usr/bin/env bash
# build_windows_exe.sh - 自动化构建 Windows .exe 安装包与便携包
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/windows"
mkdir -p "${OUTPUT_DIR}"

echo "============================================================"
echo "  [Windows Packaging] Building Windows .exe Release Bundle  "
echo "============================================================"

# 1. 编译 Rust 核心引擎
echo "[*] Step 1/3: Compiling Rust Core Engine (reader_core.dll)..."
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml" --target x86_64-pc-windows-msvc || \
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml"

# 2. 编译 Flutter Windows 客户端
echo "[*] Step 2/3: Compiling Flutter Windows Runner..."
(cd "${ROOT_DIR}/frontend" && flutter build windows --release)

# 3. 复制 DLL 与打包
echo "[*] Step 3/3: Packaging with Inno Setup into Installer .exe..."
if command -v iscc >/dev/null 2>&1; then
    iscc "${ROOT_DIR}/packaging/windows/inno_setup.iss"
    echo "[SUCCESS] Generated Windows Installer: ${OUTPUT_DIR}/AI_Reader_Setup_v1.0.0.exe"
else
    echo "[!] iscc (Inno Setup) not found. Creating portable zip bundle instead..."
    PORTABLE_ZIP="${OUTPUT_DIR}/AI_Reader_v1.0.0_Windows_x64_Portable.zip"
    (cd "${ROOT_DIR}/frontend/build/windows/x64/runner/Release" && zip -r "${PORTABLE_ZIP}" .)
    echo "[SUCCESS] Generated Windows Portable Bundle: ${PORTABLE_ZIP}"
fi
