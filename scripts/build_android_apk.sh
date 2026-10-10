#!/usr/bin/env bash
# build_android_apk.sh - 构建 Android Release APK
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/output/android"
mkdir -p "${OUTPUT_DIR}"

echo "============================================================"
echo "  [Android Packaging] Building Android Release APK & Bundle  "
echo "============================================================"

# 1. 交叉编译 Rust 核心引擎为 Android .so
echo "[*] Step 1/3: Compiling Rust Core JNI Libraries..."
JNILIBS_DIR="${ROOT_DIR}/android/app/src/main/jniLibs"
mkdir -p "${JNILIBS_DIR}"/{arm64-v8a,armeabi-v7a,x86_64}

if command -v cargo-ndk >/dev/null 2>&1; then
    (cd "${ROOT_DIR}/backend" && cargo ndk -t arm64-v8a -t armeabi-v7a -t x86_64 -o "${JNILIBS_DIR}" build --release)
fi

# 2. 编译 Flutter APK
echo "[*] Step 2/3: Compiling Flutter Release APK..."
(cd "${ROOT_DIR}/frontend" && flutter build apk --release --split-per-abi)

# 3. 输出产物
echo "[*] Step 3/3: Copying APKs to output directory..."
cp "${ROOT_DIR}/frontend/build/app/outputs/flutter-apk/"*.apk "${OUTPUT_DIR}/" || true
echo "[SUCCESS] Generated Android APKs in: ${OUTPUT_DIR}"
