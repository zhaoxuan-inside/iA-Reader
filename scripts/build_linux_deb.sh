#!/usr/bin/env bash
# build_linux_deb.sh - 构建 Debian / Ubuntu .deb 安装包
#
# 安装布局（launcher 架构：CLI 子命令 + GUI 工作台双入口）：
#   /usr/bin/ai_reader                     → sh shim（委托 /usr/lib/ai-reader/ai_reader_app.py）
#   /usr/lib/ai-reader/ai_reader_app.py    → 入口 launcher（CLI + 探测启动 Flutter bundle）
#   /usr/lib/ai-reader/backend/            → Python 引擎（CLI 数据通道，测试由 AI_READER_DB_PATH 隔离）
#   /usr/lib/ai-reader/bundle/             → Flutter GUI bundle（launcher 探测路径 APP_DIR/bundle/ai_reader）
#   /usr/lib/ai-reader/lib/libreader_core.so → Rust 引擎（GUI FFI 候选路径之一）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/linux"
# staging 树默认放本地盘：共享挂载不支持符号链接（usr/bin 相关软链会失败）
BUILD_ROOT="${BUILD_DEB_ROOT:-/tmp/ai-reader-build-deb}"
rm -rf "${BUILD_ROOT}"
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
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/usr/bin"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/backend"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/bundle"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/lib"
mkdir -p "${BUILD_ROOT}/usr/share/applications"
mkdir -p "${BUILD_ROOT}/usr/share/icons/hicolor/512x512/apps"
mkdir -p "${BUILD_ROOT}/usr/share/icons/hicolor/scalable/apps"

cp "${ROOT_DIR}/packaging/linux/deb/DEBIAN/control" "${BUILD_ROOT}/DEBIAN/"
cp -r "${ROOT_DIR}/frontend/build/linux/x64/release/bundle/"* "${BUILD_ROOT}/usr/lib/ai-reader/bundle/"
cp "${ROOT_DIR}/backend/target/release/libreader_core.so" "${BUILD_ROOT}/usr/lib/ai-reader/lib/"
cp "${ROOT_DIR}/linux/ai_reader_app.py" "${BUILD_ROOT}/usr/lib/ai-reader/ai_reader_app.py"
cp "${ROOT_DIR}/backend/reader_engine.py" "${BUILD_ROOT}/usr/lib/ai-reader/backend/"
cat > "${BUILD_ROOT}/usr/bin/ai_reader" <<'SHIM'
#!/bin/sh
# AI Reader 入口 shim：CLI 子命令与 GUI 工作台启动，真实实现见
# /usr/lib/ai-reader/ai_reader_app.py（保持 /usr/bin 稳定入口，便于桌面文件与 PATH 调用）
exec /usr/bin/python3 /usr/lib/ai-reader/ai_reader_app.py "$@"
SHIM
chmod 755 "${BUILD_ROOT}/usr/bin/ai_reader"
cp "${ROOT_DIR}/packaging/linux/ai-reader.desktop" "${BUILD_ROOT}/usr/share/applications/"
cp "${ROOT_DIR}/packaging/icon/app_icon_512.png" "${BUILD_ROOT}/usr/share/icons/hicolor/512x512/apps/ai-reader.png"
cp "${ROOT_DIR}/packaging/icon/app_icon.svg" "${BUILD_ROOT}/usr/share/icons/hicolor/scalable/apps/ai-reader.svg"

DEB_VERSION=$(grep -m1 '^Version:' "${ROOT_DIR}/packaging/linux/deb/DEBIAN/control" | awk '{print $2}')
dpkg-deb --build --root-owner-group "${BUILD_ROOT}" "${OUTPUT_DIR}/ai-reader_${DEB_VERSION}_amd64.deb"
echo "[SUCCESS] Generated Debian Package: ${OUTPUT_DIR}/ai-reader_${DEB_VERSION}_amd64.deb"
