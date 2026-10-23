# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 独立 AI 键盘面板 (FEAT-010)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-010"
  feature_name: "assistant_keyboard"
  module: "assistant"
  inherits_design_md: "/DESIGN.md"
  invoke_shortcut: "CmdOrCtrl+K"

design_tokens:
  css_variables:
    --keyboard-panel-height: "200px"
    --keycap-radius: "8px"
    --keycap-border: "1px solid #E5E7EB"
    --keycap-font: "iA Writer Mono 13px"

component_tree:
  - component: "AiKeyboardPanel"
    layout: "Bottom-docked panel (slide-in)"
    children:
      - { component: "ScopeHint", props: { scope: ["selection", "paragraph", "document"] } }
      - { component: "KeycapGrid", items: ["通俗(1)", "逻辑(2)", "批判(3)", "术语(4)", "摘要(5)"] }
    states:
      hidden: { visible: false }
      visible: { scopeResolved: true }

state_machine:
  panel:
    initial: "HIDDEN"
    states:
      HIDDEN: { on: { CMD_K: "RESOLVING" } }
      RESOLVING: { on: { SCOPE_SELECTION: "VISIBLE", SCOPE_PARAGRAPH: "VISIBLE", SCOPE_DOCUMENT: "VISIBLE" } }
      VISIBLE:
        on:
          EXECUTE_TEMPLATE: "DISPATCH"
          DIGIT_KEY: "DISPATCH"
          ESC: "HIDDEN"
          CLICK_OUTSIDE: "HIDDEN"
      DISPATCH: { on: { DONE: "HIDDEN" } }

field_constraints:
  - field: "scope"
    type: "enum"
    allowed: ["selection", "paragraph", "document"]
    default: "paragraph"
    error_message: "未选中文本，将对当前段落执行"
  - field: "template"
    type: "enum"
    allowed: ["general", "logic", "critical", "term", "summarize"]

surface_states:
  empty: { headline: "当前段落为空", desc: "将光标移到有内容的段落后再唤起 AI 键盘" }
  loading: { skeleton: "正在准备快捷操作… (5 rows)", duration_hint: "< 300ms" }
  populated: { description: "模板网格 1-5 + 作用域提示栏 + Esc 关闭提示" }
  error: { headline: "快捷操作不可用", desc: "伴读能力未就绪", recovery: "前往设置", preserve_draft: false }

executable_tests_gherkin:
  - id: "TEST-01-SUMMON-SCOPE"
    given: "阅读态且未选中文本"
    when: "按下 Cmd/Ctrl+K"
    then: "底部面板滑入；顶部提示作用域为「当前段落」"
  - id: "TEST-02-KEYCAP-EXECUTE"
    given: "面板已打开"
    when: "按数字键「2」或点击「逻辑」键帽"
    then: "以该作用域发起逻辑链伴读流"
  - id: "TEST-03-CLOSE"
    given: "面板已打开"
    when: "按 Esc 或点击外部"
    then: "面板收起，正文不变"


  - id: "TEST-04-CMDK-OPEN"
    given: "位于任意阅读界面"
    when: "按下 Cmd/Ctrl+K"
    then: "面板滑入、键帽网格可见；未选中文本时顶部明示\"未选中文本，将对当前段落执行\""

hard_guardrails:
  - "STRICTLY FORBIDDEN: 面板遮挡正文上半区（底部停靠）"
  - "STRICTLY FORBIDDEN: 无选区时直接失败（必须回退到段落作用域并提示）"
  - "STRICTLY FORBIDDEN: 使用 emoji 键帽"
  - "STRICTLY FORBIDDEN: 与划词胶囊结果重复渲染（复用同一伴读流）"
traceability:
  REQ-001: ["TEST-01-SUMMON-SCOPE"]
  REQ-002: ["TEST-01-SUMMON-SCOPE"]
  REQ-003: ["TEST-02-KEYCAP-EXECUTE"]
  REQ-004: ["TEST-03-CLOSE", "TEST-04-CMDK-OPEN"]
