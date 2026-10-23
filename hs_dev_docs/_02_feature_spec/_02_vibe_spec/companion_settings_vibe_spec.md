# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: LLM 连接与伴读设置 (FEAT-006)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-006"
  feature_name: "companion_settings"
  module: "companion"
  inherits_design_md: "/DESIGN.md"

design_tokens:
  css_variables:
    --dialog-width: "520px"
    --field-radius: "6px"
    --status-ok: "#1B873F"
    --status-fail: "#D9383A"
    --field-focus-ring: "2px #007AFF"

component_tree:
  - component: "SettingsDialog(FrostedModal)"
    layout: "Centered modal, content opaque"
    children:
      - { component: "Field", field: "base_url", label: "API 地址", placeholder: "https://api.openai.com/v1" }
      - { component: "Field", field: "api_key", label: "API Key", masked: true, placeholder: "sk-…" }
      - { component: "Field", field: "model", label: "模型", placeholder: "gpt-4o-mini" }
      - { component: "AdvancedFold", label: "高级参数 ▾", children: ["temperature", "timeout_ms", "max_retries"] }
      - { component: "StatusBadge", props: { states: ["unknown", "testing", "ok", "fail"] } }
      - { component: "Actions", buttons: ["跳过，使用离线摘要", "测试连接", "保存并启用"] }
    states:
      idle: { status: "unknown" }
      testing: { status: "testing", spinnerOnButton: true, lockWidth: true }
      ok: { status: "ok" }
      fail: { status: "fail", inlineError: "reason + fix" }

state_machine:
  settings:
    initial: "CLOSED"
    states:
      CLOSED: { on: { OPEN: "OPEN_CLEAN" } }
      OPEN_CLEAN: { on: { INPUT_CHANGE: "OPEN_DIRTY", CLOSE: "CLOSED", SKIP: "CLOSED (keep offline)" } }
      OPEN_DIRTY:
        on:
          TEST_CLICK: "TESTING"
          SAVE_CLICK: "VALIDATING"
          CLOSE: "CONFIRM_DISCARD"
          SKIP: "CLOSED"
      TESTING: { on: { OK: "OPEN_DIRTY (status=ok)", FAIL: "OPEN_DIRTY (status=fail)" } }
      VALIDATING: { on: { INVALID: "OPEN_DIRTY (inline_errors, keep_inputs)", VALID: "SAVING" } }
      SAVING: { on: { SAVED: "CLOSED (apply_immediately)" } }
      CONFIRM_DISCARD: { on: { DISCARD: "CLOSED", CANCEL: "OPEN_DIRTY" } }

field_constraints:
  - field: "base_url"
    layer: "primary_screen"
    type: "string"
    required: true
    regex: "^https?://.+$"
    max_length: 300
    error_message: "请输入以 http(s):// 开头的有效地址"
  - field: "api_key"
    layer: "primary_screen"
    type: "string"
    required: true
    min_length: 8
    masked: true
    store: "encrypted_at_rest"
    error_message: "API Key 至少 8 位，请检查后重试"
  - field: "model"
    layer: "primary_screen"
    type: "string"
    required: true
    max_length: 100
    error_message: "请填写模型名称，例如 gpt-4o-mini"
  - field: "temperature"
    layer: "progressive_fold"
    type: "number"
    min: 0.0
    max: 2.0
    default: 0.7
  - field: "timeout_ms"
    layer: "progressive_fold"
    type: "integer"
    min: 1000
    max: 120000
    default: 30000
  - field: "max_retries"
    layer: "progressive_fold"
    type: "integer"
    min: 0
    max: 5
    default: 3

surface_states:
  empty: { description: "首次打开：3 字段 + 折叠 + 跳过" }
  loading: { description: "测试连接中：spindle 与禁用按钮" }
  populated: { description: "连接正常，已保存并启用" }
  error: { description: "连接失败，保留选区，内联错误与离线回退" }

executable_tests_gherkin:
  - id: "TEST-01-TEST-CONNECT-OK"
    given: "已填入合法 base_url/api_key/model"
    when: "点击「测试连接」"
    then: "状态徽标变绿；可保存"
  - id: "TEST-02-REQUIRED-INLINE"
    given: "model 为空"
    when: "点击「保存并启用」"
    then: "model 原位红框 + 修复提示；其余字段保留"
  - id: "TEST-03-KEY-NEVER-PLAINTEXT"
    given: "保存了 API Key"
    when: "重新打开对话框"
    then: "Key 掩码显示；磁盘无明文"
  - id: "TEST-04-SKIP-OFFLINE"
    given: "用户不想配置 LLM"
    when: "点击「跳过，使用离线摘要」"
    then: "关闭对话框、原配置不变；伴读走离线降级"


  - id: "TEST-05-BASE-CONFIG-PERSIST"
    given: "打开设置对话框"
    when: "填写 Base URL / API Key / Model 并保存"
    then: "三项本地持久化；重开显示掩码，磁盘无明文密钥"
  - id: "TEST-06-ADVANCED-COLLAPSED"
    given: "打开设置对话框"
    when: " toggles 高级参数"
    then: "默认收起（▸）；展开显示温度/超时/重试三项及默认值"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 明文存储或回显 API Key"
  - "STRICTLY FORBIDDEN: 静默后台探测外部端点（必须用户显式「测试连接」）"
  - "STRICTLY FORBIDDEN: 校验失败清空已填字段"
  - "STRICTLY FORBIDDEN: 使用笼统按钮文案「确定/提交」（用「保存并启用/测试连接」）"
  - "STRICTLY FORBIDDEN: 保存需重启才生效"
traceability:
  REQ-001: ["TEST-05-BASE-CONFIG-PERSIST"]
  REQ-002: ["TEST-01-TEST-CONNECT-OK"]
  REQ-003: ["TEST-03-KEY-NEVER-PLAINTEXT","TEST-05-BASE-CONFIG-PERSIST"]
  REQ-004: ["TEST-02-REQUIRED-INLINE"]
  REQ-005: ["TEST-04-SKIP-OFFLINE"]
  REQ-006: ["TEST-06-ADVANCED-COLLAPSED"]
