#!/usr/bin/env bash
# build_linux_deb.sh - 构建 Debian / Ubuntu .deb 安装包
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/linux"
BUILD_ROOT="${ROOT_DIR}/output/build_deb"
mkdir -p "${OUTPUT_DIR}" "${BUILD_ROOT}"

echo "============================================================"
echo "  [Linux Packaging] Building Debian / Ubuntu .deb Package    "
echo "============================================================"

# 1. 编译 Rust Core
echo "[*] Step 1/3: Compiling Rust Core Engine..."
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml"

# 2. 编译 Flutter Linux
echo "[*] Step 2/3: Compiling Flutter Linux App..."
(cd "${ROOT_DIR}/frontend" && flutter build linux --release)

# 3. 组织 deb 根目录结构
echo "[*] Step 3/3: Assembling and building .deb package..."
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/usr/bin"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader"
mkdir -p "${BUILD_ROOT}/usr/share/applications"

cp "${ROOT_DIR}/packaging/linux/deb/DEBIAN/control" "${BUILD_ROOT}/DEBIAN/"
cp -r "${ROOT_DIR}/frontend/build/linux/x64/release/bundle/"* "${BUILD_ROOT}/usr/lib/ai-reader/"
cp "${ROOT_DIR}/backend/target/release/libreader_core.so" "${BUILD_ROOT}/usr/lib/ai-reader/lib/"
ln -sf /usr/lib/ai-reader/ai_reader "${BUILD_ROOT}/usr/bin/ai_reader"
cp "${ROOT_DIR}/packaging/linux/deb/usr/share/applications/ai-reader.desktop" "${BUILD_ROOT}/usr/share/applications/"

dpkg-deb --build --root-owner-group "${BUILD_ROOT}" "${OUTPUT_DIR}/ai-reader_1.0.0_amd64.deb"
echo "[SUCCESS] Generated Debian Package: ${OUTPUT_DIR}/ai-reader_1.0.0_amd64.deb"
