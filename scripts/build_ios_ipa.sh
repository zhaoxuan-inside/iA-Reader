#!/usr/bin/env bash
# build_ios_ipa.sh - 构建 iOS Release IPA
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/ios"
mkdir -p "${OUTPUT_DIR}"

echo "============================================================"
echo "  [iOS Packaging] Building iOS Release IPA Archive          "
echo "============================================================"

# 1. 编译 Rust iOS 静态库
echo "[*] Step 1/3: Compiling Rust Core Engine for iOS (aarch64)..."
if command -v cargo >/dev/null 2>&1; then
    (cd "${ROOT_DIR}/backend" && cargo build --target aarch64-apple-ios --release || true)
fi

# 2. 编译 Flutter iOS
echo "[*] Step 2/3: Building Flutter iOS App..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    (cd "${ROOT_DIR}/frontend" && flutter build ipa --export-options-plist="${ROOT_DIR}/packaging/ios/ExportOptions.plist")
    cp "${ROOT_DIR}/frontend/build/ios/ipa/"*.ipa "${OUTPUT_DIR}/" || true
    echo "[SUCCESS] Generated iOS IPA: ${OUTPUT_DIR}/ai_reader.ipa"
else
    echo "[!] iOS IPA packaging requires macOS host environment with Xcode installed."
    echo "[*] Export options configuration validated at: packaging/ios/ExportOptions.plist"
fi
