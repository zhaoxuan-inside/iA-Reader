#!/usr/bin/env bash
# build_all_platforms.sh - 全平台一键编译与打包驱动脚本
#
# 诚实门禁：deb 为主交付物，失败即整体失败；rpm/arch 依赖宿主工具链
#（rpmbuild / makepkg），缺失时显式跳过并说明，绝不静默吞错。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "    AI Reader - Multi-Platform Distribution Packaging Pipe  "
echo "============================================================"

chmod +x "${SCRIPT_DIR}"/*.sh

# 1. Linux deb（主交付物，失败即停）
echo ">>> Packaging Linux (.deb)..."
"${SCRIPT_DIR}/build_linux_deb.sh"

# 2. Linux rpm（宿主需 rpmbuild）
if command -v rpmbuild >/dev/null 2>&1; then
    echo ">>> Packaging Linux (.rpm)..."
    "${SCRIPT_DIR}/build_linux_rpm.sh"
else
    echo "[SKIP] rpm：宿主未安装 rpmbuild（spec 已就绪：packaging/linux/rpm/ai-reader.spec）"
fi

# 3. Arch 包（宿主需 makepkg）
if command -v makepkg >/dev/null 2>&1; then
    echo ">>> Packaging Linux (Arch)..."
    "${SCRIPT_DIR}/build_linux_arch.sh"
else
    echo "[SKIP] Arch：宿主未安装 makepkg（PKGBUILD 已就绪：packaging/linux/arch/PKGBUILD）"
fi

echo "============================================================"
echo "  [PACKAGES] Packaging pipeline execution finished!          "
echo "  Check output directory: output/linux                      "
echo "============================================================"
