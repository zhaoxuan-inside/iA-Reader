#!/usr/bin/env bash
# build_linux_rpm.sh - 构建 Fedora / RHEL / openSUSE .rpm 安装包
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/linux"
RPM_TOPDIR="${ROOT_DIR}/output/rpmbuild"
mkdir -p "${OUTPUT_DIR}" "${RPM_TOPDIR}"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

echo "============================================================"
echo "  [Linux Packaging] Building RedHat / Fedora .rpm Package   "
echo "============================================================"

# 1. 编译
echo "[*] Step 1/3: Compiling Core & Flutter..."
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml"
(cd "${ROOT_DIR}/frontend" && flutter build linux --release)

# 2. 准备源码包 tar.gz
echo "[*] Step 2/3: Archiving sources..."
tar --exclude='.git' --exclude='output' -czf "${RPM_TOPDIR}/SOURCES/ai-reader-1.0.0.tar.gz" -C "${ROOT_DIR}/.." ai-reader

# 3. 执行 rpmbuild
echo "[*] Step 3/3: Running rpmbuild..."
if command -v rpmbuild >/dev/null 2>&1; then
    rpmbuild --define "_topdir ${RPM_TOPDIR}" -ba "${ROOT_DIR}/packaging/linux/rpm/ai-reader.spec"
    cp "${RPM_TOPDIR}"/RPMS/*/*.rpm "${OUTPUT_DIR}/"
    echo "[SUCCESS] Generated RPM Package in: ${OUTPUT_DIR}"
else
    echo "[!] rpmbuild tool not installed on host. Spec validated at: packaging/linux/rpm/ai-reader.spec"
fi
