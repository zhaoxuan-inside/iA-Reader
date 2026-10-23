# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 多端构建与本地数据治理 (FEAT-011)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-011"
  feature_name: "platform_distribution"
  module: "platform"
  inherits_design_md: "/DESIGN.md"
  clients: ["linux", "windows", "android"]

design_tokens:
  css_variables:
    inherit_all: true   # 继承 /DESIGN.md 全部 Design Tokens   # 全量继承 /DESIGN.md

component_tree:
  - component: "DataHome"
    layout: "~/.ai-reader/{data,config,logs,books}"
    props: { overridable: true, atomic_create: true, auto_migrate_legacy: true }

state_machine:
  bootstrap:
    initial: "CHECK_HOME"
    states:
      CHECK_HOME: { on: { EXISTS: "CHECK_MIGRATION", MISSING: "CREATE_DIRS" } }
      CREATE_DIRS: { on: { OK: "INIT_DB", NOT_WRITABLE: "ERROR_ACTIONABLE" } }
      CHECK_MIGRATION: { on: { LEGACY_FOUND: "MIGRATING", NONE: "INIT_DB" } }
      MIGRATING: { on: { OK: "INIT_DB", FAIL: "ERROR_ACTIONABLE" } }
      INIT_DB: { on: { OK: "READY" } }
      READY: { on: { SET_HOME: "CHECK_HOME" } }
      ERROR_ACTIONABLE: { on: { RETRY: "CHECK_HOME", CHOOSE_PATH: "CHECK_HOME" } }

field_constraints:
  - field: "home_dir"
    type: "string"
    default: "~/.ai-reader"
    overridable: true
  - field: "sub_dirs"
    type: "list"
    const: ["data", "config", "logs", "books"]
  - field: "client_target"
    type: "enum"
    allowed: ["linux", "windows", "android"]

surface_states:
  empty: { headline: "尚无任何构建产物", desc: "在目标平台执行构建脚本后，产物会汇总到这里" }
  loading: { skeleton: "正在汇总三端构建状态… (4 rows)" }
  populated: { description: "Linux/Windows/Android 三卡 + 统一 FFI 信封说明 + output/<client> 路径" }
  error: { headline: "构建状态读取失败", desc: "请检查 output/ 目录是否存在构建产物", recovery: "重试", preserve_draft: false }

executable_tests_gherkin:
  - id: "TEST-01-FIRST-RUN-HOME"
    given: "首次启动且 home 不存在"
    when: "初始化"
    then: "原子创建四子目录；DB 与配置就位可读写"
  - id: "TEST-02-LEGACY-MIGRATION"
    given: "检测到旧位置数据"
    when: "初始化"
    then: "数据迁入新位置且无丢失；可重入幂等"
  - id: "TEST-03-NOT-WRITABLE"
    given: "目标目录不可写"
    when: "尝试初始化"
    then: "明确原因 + 修复建议；不静默失败"
  - id: "TEST-04-FFI-CONTRACT-PARITY"
    given: "同一 action/payload"
    when: "Linux/Windows/Android 分别调用"
    then: "信封结构 (code/message/data/metrics) 完全一致"
  - id: "TEST-05-OUTPUT-ISOLATION"
    given: "执行构建"
    when: "产物生成"
    then: "仅落在 output/<client>/，含四段式版本号"


  - id: "TEST-06-DATA-RELOCATE"
    given: "在设置中更改数据目录为可写新路径"
    when: "保存并重启"
    then: "新路径创建并就位，旧数据保留"
  - id: "TEST-07-OUTPUT-ISOLATION"
    given: "触发三端构建"
    when: "产物生成"
    then: "仅 output/<client>/ 下落盘，移动包带 matching map"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 数据散落在工作目录或工程根（必须集中 ~/.ai-reader）"
  - "STRICTLY FORBIDDEN: 迁移非幂等或造成数据丢失"
  - "STRICTLY FORBIDDEN: Android 发布包缺少混淆符号表 (Mapping)"
  - "STRICTLY FORBIDDEN: 三端 FFI 信封结构不一致"
  - "STRICTLY FORBIDDEN: 打包产物散落在 output/<client>/ 之外"
traceability:
  REQ-001: ["TEST-01-FIRST-RUN-HOME"]
  REQ-002: ["TEST-02-LEGACY-MIGRATION"]
  REQ-003: ["TEST-06-DATA-RELOCATE"]
  REQ-004: ["TEST-04-FFI-CONTRACT-PARITY"]
  REQ-005: ["TEST-07-OUTPUT-ISOLATION"]
  REQ-006: ["TEST-03-NOT-WRITABLE"]
