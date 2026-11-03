# AI Reader 工程门禁（质量门禁的可执行载体）
#
#   make test      → 全量测试（cargo + flutter + python 契约/端到端/CLI/规格/性能）
#   make lint      → 静态检查（clippy 零告警 + flutter analyze 零问题）
#   make bench     → 性能基准（10万字解析 / NLP / 离线卡片 SLA）
#   make build-deb → Linux deb 构建 + 产物清单/校验和同步
#   make build-apk → Android APK（arm64+x86_64，内嵌 Rust 引擎）
#   make check     → lint + test（门禁组合）
#
# 说明：
# - pytest 套件以 -I 隔离模式运行（不注入用户 site-packages）；
# - test/_00_e2e/test_installed_workbench_e2e.py 需要已安装 deb + sudo，默认不进 CI 门禁，
#   以 make test-installed 单独执行；
# - flutter 测试需要 NO_PROXY 覆盖本机回环（测试 shell 与 runner 走 127.0.0.1 通信）。

.PHONY: help test lint bench build-deb build-apk check test-installed clean

FLUTTER ?= $(shell command -v flutter 2>/dev/null || echo $(HOME)/development/flutter/bin/flutter)

help:
	@echo "make test | lint | bench | build-deb | check | test-installed | clean"

backend/target/release/libreader_core.so:
	cargo build --release --manifest-path backend/Cargo.toml

cargo-test:
	cargo test --manifest-path backend/Cargo.toml

flutter-test:
	cd frontend && NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost $(FLUTTER) test

pytest:
	python3 -I test/_03_contract_test/test_ffi_contract.py
	python3 -I test/_00_e2e/test_rust_engine_full_flow_e2e.py
	python3 -I test/_02_integration_test/test_cross_action_integration.py
	python3 -I test/_01_method_test/test_core_engine_cli.py
	python3 -I test/_01_method_test/test_frontend_specs.py

test: cargo-test flutter-test pytest
	@echo "[GATE] all tests passed"

lint:
	cargo clippy --manifest-path backend/Cargo.toml --all-targets -- -D warnings
	cd frontend && $(FLUTTER) analyze

bench:
	python3 -I test/_05_performance_test/test_reader_performance_benchmark.py

check: lint test

build-deb:
	./scripts/build_linux_deb.sh

# Android APK（需 ~/ai-reader-android-tools：JDK17 + SDK + NDK，见脚本头注释）
build-apk:
	./scripts/build_android_apk.sh

test-installed:
	python3 -I test/_00_e2e/test_installed_workbench_e2e.py

clean:
	cargo clean --manifest-path backend/Cargo.toml
	cd frontend && $(FLUTTER) clean
