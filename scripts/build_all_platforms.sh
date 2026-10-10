#!/usr/bin/env bash
# build_all_platforms.sh - 全平台一键编译与打包驱动脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "    AI Reader - Multi-Platform Distribution Packaging Pipe  "
echo "============================================================"

chmod +x "${SCRIPT_DIR}"/*.sh

# 1. Linux 打包 (deb, rpm, arch)
echo ">>> [1/4] Packaging Linux (.deb, .rpm, Arch PKGBUILD)..."
"${SCRIPT_DIR}/build_linux_deb.sh" || true
"${SCRIPT_DIR}/build_linux_rpm.sh" || true
"${SCRIPT_DIR}/build_linux_arch.sh" || true

# 2. Windows 打包 (.exe / portable)
echo ">>> [2/4] Packaging Windows (.exe)..."
"${SCRIPT_DIR}/build_windows_exe.sh" || true

# 3. Android 打包 (.apk)
echo ">>> [3/4] Packaging Android (.apk)..."
"${SCRIPT_DIR}/build_android_apk.sh" || true

# 4. iOS 打包 (.ipa)
echo ">>> [4/4] Packaging iOS (.ipa)..."
"${SCRIPT_DIR}/build_ios_ipa.sh" || true

echo "============================================================"
echo "  [ALL PACKAGES] Packaging pipeline execution finished!      "
echo "  Check output directory: output/                           "
echo "============================================================"
