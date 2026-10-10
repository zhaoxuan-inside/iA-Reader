#!/usr/bin/env bash
# build_all_platforms.sh - 全平台一键编译与打包驱动脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "    AI Reader - Multi-Platform Distribution Packaging Pipe  "
echo "============================================================"

chmod +x "${SCRIPT_DIR}"/*.sh

# 1. Linux 打包 (deb, rpm, arch)
echo ">>> Packaging Linux CLI (.deb, .rpm, Arch PKGBUILD)..."
"${SCRIPT_DIR}/build_linux_deb.sh" || true
"${SCRIPT_DIR}/build_linux_rpm.sh" || true
"${SCRIPT_DIR}/build_linux_arch.sh" || true

echo "============================================================"
echo "  [PACKAGES] Packaging pipeline execution finished!          "
echo "  Check output directory: output/linux                      "
echo "============================================================"
