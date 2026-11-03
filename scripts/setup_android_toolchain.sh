#!/usr/bin/env bash
# setup_android_toolchain.sh - Android 构建工具链一键安装（幂等）
#
# 安装到 ~/ai-reader-android-tools/：JDK 17 + Android SDK + NDK + Gradle 发行版。
# 已存在的组件自动跳过；配合 scripts/build_android_apk.sh 使用。
# 用法：bash scripts/setup_android_toolchain.sh [--with-flutter]
set -euo pipefail

TOOLS="${AI_READER_ANDROID_TOOLS:-$HOME/ai-reader-android-tools}"
DL="$TOOLS/dl"
mkdir -p "$TOOLS" "$DL"

echo "============================================================"
echo "  [Android Toolchain] Installing to $TOOLS"
echo "============================================================"

fetch() { # fetch <url> <dest>
    if [ -f "$2" ] && [ "$(stat -c%s "$2")" -gt 1000000 ]; then
        echo "[skip] $2 已存在"
    else
        echo "[fetch] $1"
        curl -sL --retry 3 -o "$2" "$1"
    fi
}

# ---------- JDK 17 ----------
if [ ! -x "$TOOLS/jdk/bin/java" ]; then
    fetch "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse" "$DL/jdk17.tar.gz"
    tar -xzf "$DL/jdk17.tar.gz" -C "$TOOLS"
    mv "$TOOLS"/jdk-17* "$TOOLS/jdk"
    rm -f "$DL/jdk17.tar.gz"
fi
export JAVA_HOME="$TOOLS/jdk"
export PATH="$JAVA_HOME/bin:$PATH"
echo "[ok] JDK: $(java -version 2>&1 | head -1)"

# ---------- Android SDK ----------
if [ ! -x "$TOOLS/sdk/cmdline-tools/latest/bin/sdkmanager" ]; then
    fetch "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" "$DL/cmdtools.zip"
    unzip -q "$DL/cmdtools.zip" -d "$TOOLS/sdk-tmp"
    mkdir -p "$TOOLS/sdk/cmdline-tools"
    mv "$TOOLS/sdk-tmp/cmdline-tools" "$TOOLS/sdk/cmdline-tools/latest"
    rm -rf "$TOOLS/sdk-tmp" "$DL/cmdtools.zip"
fi
export ANDROID_HOME="$TOOLS/sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
yes | sdkmanager --licenses >/dev/null 2>&1 || true
sdkmanager --install "platform-tools" "platforms;android-36" "build-tools;36.0.0" >/dev/null
echo "[ok] SDK: $(ls "$ANDROID_HOME/platforms" | tr '\n' ' ')"

# ---------- NDK（与 flutter 默认 ndkVersion 28.2.13676358 同代的 r28b；r27c 亦兼容）----------
if [ ! -f "$TOOLS/ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android24-clang" ]; then
    fetch "https://dl.google.com/android/repository/android-ndk-r28b-linux.zip" "$DL/ndk.zip"
    unzip -q "$DL/ndk.zip" -d "$TOOLS"
    mv "$TOOLS"/android-ndk-r28b "$TOOLS/ndk"
    rm -f "$DL/ndk.zip"
fi
export ANDROID_NDK_HOME="$TOOLS/ndk"
echo "[ok] NDK: $(grep -m1 Pkg.Revision "$ANDROID_NDK_HOME/source.properties" | cut -d= -f2)"

# ---------- Gradle 发行版（预置进 wrapper 哈希目录，免 flutter 构建时下载）----------
GH="${BUILD_APK_ROOT:-/tmp/ai-reader-build-apk}-gradle-home/wrapper/dists/gradle-9.3.1-bin/23ovyewtku6u96viwx3xl3oks"
if [ ! -f "$GH/gradle-9.3.1/bin/gradle" ]; then
    fetch "https://services.gradle.org/distributions/gradle-9.3.1-bin.zip" "$DL/gradle.zip"
    mkdir -p "$GH"
    unzip -q "$DL/gradle.zip" -d "$GH"
    touch "$GH/gradle-9.3.1-bin.zip.ok"
    mv "$DL/gradle.zip" "$GH/gradle-9.3.1-bin.zip"
fi
echo "[ok] Gradle 9.3.1: $GH"

# ---------- 可选：Flutter SDK ----------
if [ "${1:-}" = "--with-flutter" ] && [ ! -x "$TOOLS/flutter/bin/flutter" ]; then
    STABLE_JSON="https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json"
    ARCHIVE=$(curl -sL "$STABLE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); h=d['current_release']['stable']; r=next(x for x in d['releases'] if x['hash']==h); print(r['archive'])")
    fetch "https://storage.googleapis.com/flutter_infra_release/releases/$ARCHIVE" "$DL/flutter.tar.xz"
    mkdir -p "$TOOLS/flutter-staging"
    tar -xJf "$DL/flutter.tar.xz" -C "$TOOLS/flutter-staging"
    rm -rf "$TOOLS/flutter"
    mv "$TOOLS/flutter-staging/flutter" "$TOOLS/flutter"
    rm -rf "$TOOLS/flutter-staging" "$DL/flutter.tar.xz"
fi

echo "[SUCCESS] Android 工具链就绪：$TOOLS"
