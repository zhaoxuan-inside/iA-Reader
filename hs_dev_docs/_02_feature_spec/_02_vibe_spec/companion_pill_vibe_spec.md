# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 划词伴读胶囊 (FEAT-004)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-004"
  feature_name: "companion_pill"
  module: "companion"
  inherits_design_md: "/DESIGN.md"
  reveal_budget_ms: 50

design_tokens:
  css_variables:
    --pill-bg: "#FFFFFF"
    --pill-border: "1px solid #E5E7EB"
    --pill-radius: "20px"
    --pill-offset-y: "10px"
    --pill-label-font: "iA Writer Mono 12px"
    --pill-hover-accent: "#007AFF"
    --dark-pill-bg: "#18181B"

component_tree:
  - component: "FloatingActionPill"
    layout: "Overlay anchored to selection rect (TapRegion)"
    props: { borderRadius: "20px", shadow: "none", followSelection: true, clampToViewport: true }
    children:
      - { type: "PillLabel", text: "通俗", snippet: "general" }
      - { type: "PillLabel", text: "逻辑", snippet: "logic" }
      - { type: "PillLabel", text: "批判", snippet: "critical" }
      - { type: "PillLabel", text: "术语", snippet: "term" }
      - { type: "PillLabel", text: "高亮", snippet: "highlight" }
    states:
      default: { bg: "var(--pill-bg)", border: "var(--pill-border)" }
      hover: { color: "var(--pill-hover-accent)" }
      hidden: { visible: false }

state_machine:
  pill:
    initial: "HIDDEN"
    states:
      HIDDEN: { on: { SELECTION_NONEMPTY: "VISIBLE" } }
      VISIBLE:
        on:
          CLICK_OUTSIDE: "HIDDEN"
          SELECTION_CLEARED: "HIDDEN"
          CLICK_TEMPLATE: "DISPATCH"
          CLICK_HIGHLIGHT: "HIGHLIGHT_FLOW"
      DISPATCH: { on: { LLM_READY: "OPEN_COMPANION", LLM_UNCONFIGURED: "OPEN_SETTINGS_GUIDE" } }
      HIGHLIGHT_FLOW: { on: { DONE: "HIDDEN" } }
      OPEN_SETTINGS_GUIDE: { on: { CANCEL: "VISIBLE", SAVED: "OPEN_COMPANION" } }

field_constraints:
  - field: "selection_text"
    type: "string"
    min_length: 1
    max_length: 2000
    error_message: "请选择一段文本来发起伴读"
  - field: "pill_offset_y"
    type: "integer"
    const: 10
  - field: "template"
    type: "enum"
    allowed: ["general", "logic", "critical", "term", "highlight"]

surface_states:
  empty: { description: "未选中文字隐藏；未配置 LLM 时点击模板引导至设置" }
  loading: { description: "胶囊占位中，不阻塞正文" }
  populated: { description: "药丸含选区摘录与五标签" }
  error: { description: "伴读未就绪，引导而非报错" }

executable_tests_gherkin:
  - id: "TEST-01-PILL-REVEAL-ANCHOR"
    given: "阅读态"
    when: "鼠标划选一句并松开"
    then: "50ms 内选区下方 10px 出现纯色药丸，跟随选区并夹紧窗口"
  - id: "TEST-02-NO-EMOJI-LABELS"
    given: "药丸可见"
    when: "渲染标签"
    then: "显示 [通俗][逻辑][批判][术语][高亮] mono 文字，无 emoji"
  - id: "TEST-03-CLICK-OUTSIDE-DISMISS"
    given: "药丸可见"
    when: "点击正文任意处"
    then: "药丸与选区同步收起"
  - id: "TEST-04-EDGE-FLIP"
    given: "选区贴近窗口底边"
    when: "药丸展示"
    then: "翻转到选区上方 10px，完整可见"
  - id: "TEST-05-UNCONFIGURED-GUIDE"
    given: "未配置 LLM"
    when: "点击「通俗」"
    then: "打开设置引导而非报错；取消后选区不丢失"


  - id: "TEST-06-TAG-SEMANTICS"
    given: "划선文本后胶囊浮出"
    when: "依次点击 5 个 mono 文字标签"
    then: "4 认知模板分别启动流式伴读；\"高亮\"切换样式并写入标注列表；所有标签无 emoji"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 使用 emoji 图标（mono 文字标签）"
  - "STRICTLY FORBIDDEN: 药丸带投影或彩色渐变（纯色 + 1px 边框，零阴影）"
  - "STRICTLY FORBIDDEN: 药丸溢出窗口可视范围"
  - "STRICTLY FORBIDDEN: 未配置 LLM 时抛错中断阅读（必须走设置引导）"
traceability:
  REQ-001: ["TEST-01-PILL-REVEAL-ANCHOR"]
  REQ-002: ["TEST-06-TAG-SEMANTICS"]
  REQ-003: ["TEST-03-CLICK-OUTSIDE-DISMISS","TEST-06-TAG-SEMANTICS"]
  REQ-004: ["TEST-04-EDGE-FLIP"]
  REQ-005: ["TEST-05-UNCONFIGURED-GUIDE"]
