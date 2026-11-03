#!/usr/bin/env bash
# build_android_apk.sh - 构建 Android APK（arm64 + x86_64，内嵌 Rust 引擎）
#
# 流程：cargo 交叉编译 libreader_core.so（NDK 工具链）→ 注入 jniLibs →
#       本地盘 staging 规避共享挂限 → flutter build apk --release → 产物回拷。
#
# 环境要求（可由 AI_READER_ANDROID_TOOLS 指定，缺省 ~/ai-reader-android-tools）：
#   $TOOLS/jdk/           JDK 17+
#   $TOOLS/sdk/           Android SDK（platforms;android-36, build-tools, platform-tools）
#   $TOOLS/ndk/           Android NDK（flutter 默认 28.2.13676358 / r28b）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="${AI_READER_ANDROID_TOOLS:-$HOME/ai-reader-android-tools}"
OUTPUT_DIR="${ROOT_DIR}/output/android"
BUILD_ROOT="${BUILD_APK_ROOT:-/tmp/ai-reader-build-apk}"

# 工具链入 PATH
# flutter 不在 PATH 时回退默认安装位（与 build_linux_deb.sh 口径一致）
if ! command -v flutter >/dev/null 2>&1; then
    PATH="$HOME/development/flutter/bin:$PATH"
    export PATH
fi
export JAVA_HOME="${JAVA_HOME:-$TOOLS/jdk}"
export ANDROID_HOME="${ANDROID_HOME:-$TOOLS/sdk}"
# Gradle 缓存独立于仓库树；优先播种本机共享缓存（免 gradle 发行版大下载）
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-${BUILD_ROOT}-gradle-home}"
mkdir -p "${GRADLE_USER_HOME}/wrapper/dists"
SEED_DISTS="/home/hardstone/Share/Common/Data/gradle/wrapper/dists"
if [ -d "${SEED_DISTS}" ]; then
    cp -rn "${SEED_DISTS}"/* "${GRADLE_USER_HOME}/wrapper/dists/" 2>/dev/null || true
fi
export ANDROID_HOME="${ANDROID_HOME:-$TOOLS/sdk}"
export ANDROID_NDK_HOME="${ANDROID_NDK_HOME:-$TOOLS/ndk}"
# Gradle JVM 不读 http_proxy 环境变量：从环境代理派生 systemProp（maven 依赖下载用）
if [ -n "${https_proxy:-}" ]; then
    _hp="${https_proxy#*//}"; _ph="${_hp%%:*}"; _pp="${_hp##*:}"
    export GRADLE_OPTS="${GRADLE_OPTS:-} -Dhttp.proxyHost=${_ph} -Dhttp.proxyPort=${_pp} -Dhttps.proxyHost=${_ph} -Dhttps.proxyPort=${_pp} -Dhttp.nonProxyHosts=localhost|127.0.0.1"
fi
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

rm -rf "${BUILD_ROOT}"
mkdir -p "${OUTPUT_DIR}" "${BUILD_ROOT}"

echo "============================================================"
echo "  [Android Packaging] Building release APK (arm64 + x86_64)  "
echo "============================================================"

# 1. Rust 引擎交叉编译（cdylib；无 JNI 依赖，Dart FFI dlopen 直取）。
#    NDK 工具链需同时在 PATH（cc-rs 探测）与 CC/CXX/AR（bundled SQLite C 编译）
echo "[*] Step 1/4: Cross-compiling libreader_core.so (aarch64 / x86_64)..."
NDK_TOOLCHAIN="${ANDROID_NDK_HOME}/toolchains/llvm/prebuilt/linux-x86_64/bin"
export PATH="${NDK_TOOLCHAIN}:${PATH}"
export CC_aarch64_linux_android="${NDK_TOOLCHAIN}/aarch64-linux-android24-clang"
export CXX_aarch64_linux_android="${NDK_TOOLCHAIN}/aarch64-linux-android24-clang++"
export AR_aarch64_linux_android="${NDK_TOOLCHAIN}/llvm-ar"
export CC_x86_64_linux_android="${NDK_TOOLCHAIN}/x86_64-linux-android24-clang"
export CXX_x86_64_linux_android="${NDK_TOOLCHAIN}/x86_64-linux-android24-clang++"
export AR_x86_64_linux_android="${NDK_TOOLCHAIN}/llvm-ar"
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml" \
    --target aarch64-linux-android \
    --config "target.aarch64-linux-android.linker=\"${NDK_TOOLCHAIN}/aarch64-linux-android24-clang\""
cargo build --release --manifest-path "${ROOT_DIR}/backend/Cargo.toml" \
    --target x86_64-linux-android \
    --config "target.x86_64-linux-android.linker=\"${NDK_TOOLCHAIN}/x86_64-linux-android24-clang\""

# 2. 本地盘 staging（gradle/插件在共享挂载上既慢又易碎；tar 前不改动源树，
#    避免 "file changed as we read it" 竞争）
echo "[*] Step 2/4: Staging frontend to local disk..."
(
  cd "${ROOT_DIR}/frontend" \
    && tar --exclude=./build --exclude=./.dart_tool --exclude=./.idea --exclude=.git \
           --exclude=./android/app/src/main/jniLibs -cf - . \
    | tar -xf - -C "${BUILD_ROOT}"
)

# 3. 注入 jniLibs（注入 staging 源树而非共享盘源树；构建产物不入库）
echo "[*] Step 3/4: Injecting engine .so into jniLibs (staging)..."
JNI="${BUILD_ROOT}/android/app/src/main/jniLibs"
mkdir -p "${JNI}/arm64-v8a" "${JNI}/x86_64"
cp "${ROOT_DIR}/backend/target/aarch64-linux-android/release/libreader_core.so" "${JNI}/arm64-v8a/"
cp "${ROOT_DIR}/backend/target/x86_64-linux-android/release/libreader_core.so" "${JNI}/x86_64/"
(
  cd "${BUILD_ROOT}" \
    && flutter pub get \
    && flutter build apk --release \
        --target-platform android-arm64,android-x64 \
        --build-name "$(cat "${ROOT_DIR}/VERSION" | tr -d '[:space:]')"
)

# 4. 产物回拷 + 校验
echo "[*] Step 4/4: Collecting artifacts..."
APK_SRC="${BUILD_ROOT}/build/app/outputs/flutter-apk/app-release.apk"
test -f "${APK_SRC}" || { echo "[ERROR] APK 未产出"; exit 1; }
# 内容完整性：引擎 .so 必须在包内（ABI 与目标平台一一对应）。
# 注意：pipefail 下 `unzip | grep -q` 会因 grep 提前退出触发 SIGPIPE 假阴性，
# 必须先取全量列表再匹配
APK_LIST="$(unzip -l "${APK_SRC}")"
echo "${APK_LIST}" | grep -q "lib/arm64-v8a/libreader_core.so" \
    || { echo "[ERROR] APK 缺少 arm64-v8a 引擎库"; exit 1; }
echo "${APK_LIST}" | grep -q "lib/x86_64/libreader_core.so" \
    || { echo "[ERROR] APK 缺少 x86_64 引擎库"; exit 1; }

cp "${APK_SRC}" "${OUTPUT_DIR}/ai-reader_$(cat "${ROOT_DIR}/VERSION" | tr -d '[:space:]')_arm64_x64.apk"
echo "[SUCCESS] Generated APK: ${OUTPUT_DIR}/"*.apk
python3 "${ROOT_DIR}/scripts/package_dist.py" --manifest-only
