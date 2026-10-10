#!/usr/bin/env bash
# build_linux_arch.sh - 构建 Arch Linux (.pkg.tar.zst) 安装包
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/linux"
ARCH_BUILD_DIR="${ROOT_DIR}/output/archbuild"
mkdir -p "${OUTPUT_DIR}" "${ARCH_BUILD_DIR}"

echo "============================================================"
echo "  [Linux Packaging] Building Arch Linux .pkg.tar.zst Package "
echo "============================================================"

# 准备打包目录
cp "${ROOT_DIR}/packaging/linux/arch/PKGBUILD" "${ARCH_BUILD_DIR}/"
tar --exclude='.git' --exclude='output' -czf "${ARCH_BUILD_DIR}/ai-reader-1.0.0.tar.gz" -C "${ROOT_DIR}/.." ai-reader

if command -v makepkg >/dev/null 2>&1; then
    (cd "${ARCH_BUILD_DIR}" && makepkg -f)
    cp "${ARCH_BUILD_DIR}"/*.pkg.tar.zst "${OUTPUT_DIR}/"
    echo "[SUCCESS] Generated Arch Package: ${OUTPUT_DIR}/*.pkg.tar.zst"
else
    echo "[!] makepkg not installed on this host. PKGBUILD validated at: packaging/linux/arch/PKGBUILD"
fi
