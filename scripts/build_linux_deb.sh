#!/usr/bin/env bash
# build_linux_deb.sh - 构建 Debian / Ubuntu .deb 安装包
#
# 安装布局（单一 Rust 引擎，GUI/CLI 双宿主）：
#   /usr/bin/ai_reader                        → sh shim：无参起 GUI，带参转发 CLI
#   /usr/lib/ai-reader/bundle/                → Flutter GUI bundle（bundle/ai_reader）
#   /usr/lib/ai-reader/bin/ai-reader-cli      → 无头 CLI（与 GUI 共用 libreader_core）
#   /usr/lib/ai-reader/lib/libreader_core.so  → Rust 引擎（唯一事实源）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# flutter 不在 PATH 时回退默认安装位（与 Makefile 的 FLUTTER 解析一致）
if ! command -v flutter >/dev/null 2>&1; then
    PATH="$HOME/development/flutter/bin:$PATH"
    export PATH
fi
OUTPUT_DIR="${ROOT_DIR}/output/linux"
# staging 树默认放本地盘：共享挂载不支持符号链接（usr/bin 相关软链会失败）
BUILD_ROOT="${BUILD_DEB_ROOT:-/tmp/ai-reader-build-deb}"
rm -rf "${BUILD_ROOT}"
mkdir -p "${OUTPUT_DIR}" "${BUILD_ROOT}"

echo "============================================================"
echo "  [Linux Packaging] Building Debian / Ubuntu .deb Package    "
echo "============================================================"

# 1. 编译 Rust Core（cdylib 引擎 + 无头 CLI）
echo "[*] Step 1/3: Compiling Rust Core Engine..."
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml"

# 2. 编译 Flutter Linux（本地盘 staging：共享挂载不支持插件 .plugin_symlinks 符号链接）
echo "[*] Step 2/3: Compiling Flutter Linux App..."
FLUTTER_STAGING="$(mktemp -d /tmp/ai-reader-flutter-XXXXXX)"
(
  cd "${ROOT_DIR}/frontend" \
    && tar --exclude=./build --exclude=./.dart_tool --exclude=./.idea --exclude=.git -cf - . \
    | tar -xf - -C "${FLUTTER_STAGING}" \
    && cd "${FLUTTER_STAGING}" \
    && flutter pub get \
    && flutter build linux --release
)
mkdir -p "${ROOT_DIR}/frontend/build/linux/x64/release"
rm -rf "${ROOT_DIR}/frontend/build/linux/x64/release/bundle"
cp -a "${FLUTTER_STAGING}/build/linux/x64/release/bundle" "${ROOT_DIR}/frontend/build/linux/x64/release/"
rm -rf "${FLUTTER_STAGING}"

# 3. 组织 deb 根目录结构
echo "[*] Step 3/3: Assembling and building .deb package..."
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/usr/bin"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/bin"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/bundle"
mkdir -p "${BUILD_ROOT}/usr/lib/ai-reader/lib"
mkdir -p "${BUILD_ROOT}/usr/share/applications"
mkdir -p "${BUILD_ROOT}/usr/share/icons/hicolor/512x512/apps"
mkdir -p "${BUILD_ROOT}/usr/share/icons/hicolor/scalable/apps"

cp "${ROOT_DIR}/packaging/linux/deb/DEBIAN/control" "${BUILD_ROOT}/DEBIAN/"
cp -r "${ROOT_DIR}/frontend/build/linux/x64/release/bundle/"* "${BUILD_ROOT}/usr/lib/ai-reader/bundle/"
cp "${ROOT_DIR}/backend/target/release/libreader_core.so" "${BUILD_ROOT}/usr/lib/ai-reader/lib/"
cp "${ROOT_DIR}/backend/target/release/ai-reader-cli" "${BUILD_ROOT}/usr/lib/ai-reader/bin/"
cat > "${BUILD_ROOT}/usr/bin/ai_reader" <<'SHIM'
#!/bin/sh
# AI Reader 稳定入口：无参启动 GUI 工作台；带参转发无头 CLI
#（CLI 与 GUI 共用 libreader_core，同一 action 两种宿主行为一致）
if [ "$#" -eq 0 ]; then
    exec /usr/lib/ai-reader/bundle/ai_reader
fi
exec /usr/lib/ai-reader/bin/ai-reader-cli "$@"
SHIM
chmod 755 "${BUILD_ROOT}/usr/bin/ai_reader"
cp "${ROOT_DIR}/packaging/linux/ai-reader.desktop" "${BUILD_ROOT}/usr/share/applications/"
cp "${ROOT_DIR}/packaging/icon/app_icon_512.png" "${BUILD_ROOT}/usr/share/icons/hicolor/512x512/apps/ai-reader.png"
cp "${ROOT_DIR}/packaging/icon/app_icon.svg" "${BUILD_ROOT}/usr/share/icons/hicolor/scalable/apps/ai-reader.svg"

DEB_VERSION=$(grep -m1 '^Version:' "${ROOT_DIR}/packaging/linux/deb/DEBIAN/control" | awk '{print $2}')
dpkg-deb --build --root-owner-group "${BUILD_ROOT}" "${OUTPUT_DIR}/ai-reader_${DEB_VERSION}_amd64.deb"
echo "[SUCCESS] Generated Debian Package: ${OUTPUT_DIR}/ai-reader_${DEB_VERSION}_amd64.deb"

# 4. 产物清单与校验和同步生成（manifest 永不落后于实际产物）
echo "[*] Step 4/4: Refreshing package manifest & checksums..."
python3 "${ROOT_DIR}/scripts/package_dist.py" --manifest-only
