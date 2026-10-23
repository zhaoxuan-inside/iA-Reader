# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 流式认知伴读卡片与原位追问 (FEAT-005)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-005"
  feature_name: "companion_stream"
  module: "companion"
  inherits_design_md: "/DESIGN.md"
  ttft_budget_ms: 800
  fallback_budget_ms: 10

design_tokens:
  css_variables:
    --modal-blur-sigma: "14"
    --modal-glow-blur: "40,90,150"
    --modal-width: "440px"
    --modal-enter: "240ms fade + scale 0.96->1.0"
    --card-bg: "#FFFFFF"
    --card-border: "1px solid #E5E7EB"
    --dark-card-bg: "#18181B"

component_tree:
  - component: "FrostedModal(CompanionCard)"
    layout: "Centered modal over gaussian-blurred backdrop (click outside closes)"
    props: { width: "440px", maxHeight: "600px", contentOpaque: true }
    children:
      - { component: "CardHeader", elements: ["[模板 · TTFT xxxms] mono", "存为边注", "✕ 收起"] }
      - { component: "StreamingBody", props: { appendMode: "token", autoScroll: true } }
      - { component: "FollowUpInput", props: { placeholder: "追问本段细节...", singleLine: true, submitOnEnter: true } }
    states:
      idle: { body: "" }
      streaming: { body: "…逐字追加", header: "[模板 · TTFT xxxms]" }
      fallback: { badge: "离线降级", body: "local_heuristic_summary" }
      error: { retryAction: "restart_stream", preserveSelection: true }

state_machine:
  stream:
    initial: "IDLE"
    states:
      IDLE: { on: { TEMPLATE_CLICK: "REQUESTING" } }
      REQUESTING:
        on:
          FIRST_TOKEN: "STREAMING (record ttft_ms)"
          HTTP_ERROR: "BACKOFF"
          TIMEOUT: "BACKOFF"
      BACKOFF: { on: { RETRIES_EXHAUSTED: "FALLBACK", RETRY_OK: "STREAMING" } }
      STREAMING: { on: { DONE: "DONE", FOLLOWUP_SUBMIT: "REQUESTING (append_to_same_card)" } }
      FALLBACK: { on: { DISMISS: "IDLE" } }
      DONE: { on: { SAVE_NOTE: "SAVED", FOLLOWUP_SUBMIT: "REQUESTING", CLOSE: "CLOSED" } }
      SAVED: { on: { DONE: "DONE" } }

field_constraints:
  - field: "template"
    type: "enum"
    allowed: ["general", "logic", "critical", "term"]
  - field: "ttft_ms"
    type: "integer"
    min: 0
    mono: true
    tabular_nums: true
  - field: "follow_up_text"
    type: "string"
    max_length: 500
    required: false
    error_message: "请输入要追问的内容"
  - field: "max_retries"
    type: "integer"
    min: 0
    max: 5
    default: 3

surface_states:
  empty: { description: "未选文本时不显示卡片；选区仍保留" }
  loading: { description: "骨架屏 (4 行)；保留选区不阻断；FALLBACK 路径可 < 10ms 本地" }
  populated: { description: "毛玻璃遮罩 + 440px 卡片（header/streaming body/follow-up）；header TTFT badge" }
  error: { headline: "! 连接失败", desc: "端点无响应；已保留选区；Retry / 离线摘要；preserveSelection: true", recovery: "重新生成 / 用离线摘要" }

executable_tests_gherkin:
  - id: "TEST-01-STREAM-TTFT"
    given: "已配置可用 LLM 且已划选文本"
    when: "点击「逻辑」"
    then: "800ms 内开始逐字流式输出；头部显示 [逻辑链推理 · TTFT xxxms]"
  - id: "TEST-02-FOLLOWUP-INLINE"
    given: "卡片已有内容"
    when: "提交底部追问"
    then: "答复以流式追加在同一卡片流内，上下文连续"
  - id: "TEST-03-FALLBACK"
    given: "网络不可达/超时"
    when: "点击「通俗」"
    then: "退避重试后用本地启发式摘要（< 10ms），标注「离线降级」"
  - id: "TEST-04-SAVE-NOTE-IDEMPOTENT"
    given: "卡片有内容"
    when: "连续两次点击「存为边注」"
    then: "仅一条边注；二次提示「已归档为边注」"


  - id: "TEST-05-HEADER-TTFT"
    given: "任一模板已流式异步进行"
    when: "至少一个 token 到达"
    then: "header 显示 `[模板 · TTFT xxxms]` mono tabular-nums；✕ 收起可关闭"
  - id: "TEST-06-REOPEN-CONTEXT"
    given: "已收起有过历史追问的伴读卡片"
    when: "对同一选区重新选择模板"
    then: "上下文一致，历史追问随卡片保留"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 失败或超时清空卡片/丢失选区（必须降级或原位重试）"
  - "STRICTLY FORBIDDEN: 一次性整段返回替代流式（必须逐字追加）"
  - "STRICTLY FORBIDDEN: 卡片使用描边硬边框或彩色背景"
  - "STRICTLY FORBIDDEN: 重复归档产生多条边注"
  - "STRICTLY FORBIDDEN: 空白等待屏（无 TTFT 占位/无降级）"
traceability:
  REQ-001: ["TEST-01-STREAM-TTFT"]
  REQ-002: ["TEST-05-HEADER-TTFT"]
  REQ-003: ["TEST-02-FOLLOWUP-INLINE","TEST-06-REOPEN-CONTEXT"]
  REQ-004: ["TEST-04-SAVE-NOTE-IDEMPOTENT","TEST-05-HEADER-TTFT"]
  REQ-005: ["TEST-03-FALLBACK"]
  REQ-006: ["TEST-06-REOPEN-CONTEXT"]
