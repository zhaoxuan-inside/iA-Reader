# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 聚焦模式与顶栏隐退 (FEAT-003)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-003"
  feature_name: "reader_focus_mode"
  module: "reader"
  inherits_design_md: "/DESIGN.md"

design_tokens:
  css_variables:
    --dim-opacity: "0.65"
    --focus-transition: "150ms ease-out"
    --header-idle-timeout: "3000ms"
    --header-height: "44px"

component_tree:
  - component: "FocusModeDimLayer"
    props: { dimOpacity: 0.65, activeParagraphOpacity: 1.0, reducedMotionInstant: true }
  - component: "MinimalChromeHeader"
    props: { autohide: true, idleTimeoutMs: 3000, revealOn: ["scroll_up", "edge_pointer_dwell"], suppressOn: ["edge_pointer_pass_only"] }

state_machine:
  focus_mode:
    initial: "OFF"
    states:
      OFF: { on: { CMD_D: "ON", SELECT_FOR_COMPANION: "ON" } }
      ON: { on: { ESC: "OFF", DBLCLICK_BLANK: "OFF", COMPANION_CLOSED: "OFF" } }
  hyper_focus:
    initial: "OFF"
    states:
      OFF: { on: { CMD_SHIFT_F: "ON" } }
      ON: { on: { ESC: "OFF" } }
  header_visibility:
    initial: "VISIBLE"
    states:
      VISIBLE: { on: { SCROLL_DOWN: "HIDING", IDLE_3S: "HIDING" } }
      HIDING: { on: { HIDDEN_ANIM_DONE: "HIDDEN" } }
      HIDDEN: { on: { SCROLL_UP: "VISIBLE", EDGE_POINTER_DWELL: "VISIBLE" } }

field_constraints:
  - field: "focus_mode"
    type: "boolean"
    default: false
    persisted_per_document: true
  - field: "dim_opacity"
    type: "number"
    const: 0.65
  - field: "header_idle_timeout_ms"
    type: "integer"
    const: 3000

surface_states:
  empty: { description: "直接随父表面 reader_render 的 Empty/Loading/Error 状态；专注模式本身无独立数据源" }
  loading: { description: "父表面过渡期间保持上一帧 + skeleton" }
  populated: { description: "当前段 100% / 其余 65%，顶栏 fades，Esc 退出；prefers-reduced-motion 全 0ms" }
  error: { description: "复用 reader_render error banner，focus 状态重置" }

executable_tests_gherkin:
  - id: "TEST-01-FOCUS-PARAGRAPH"
    given: "多段文档处于阅读态"
    when: "按下 Cmd/Ctrl+D"
    then: "当前段 100%，其余段 0.65 透明度，150ms 过渡"
  - id: "TEST-02-HEADER-AUTOHIDE"
    given: "顶栏可见"
    when: "向下滚动"
    then: "顶栏淡出；向上滚动或边缘指针停留后淡入"
  - id: "TEST-03-ESC-RESTORE"
    given: "处于聚焦模式"
    when: "按 Esc"
    then: "100ms 内全屏恢复 100% 对比度"
  - id: "TEST-04-REDUCED-MOTION"
    given: "系统 prefers-reduced-motion"
    when: "切换聚焦/顶栏"
    then: "瞬时切换，无动画"


  - id: "TEST-06-SUPER-FOCUS"
    given: "段落聚焦进行中"
    when: "按下 Cmd/Ctrl+Shift+F"
    then: "除正文外零元素；Esc 退出恢复"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 指针仅在边缘路过即唤出顶栏（仅 scroll_up / dwell 唤出，防抖动）"
  - "STRICTLY FORBIDDEN: 聚焦态使用非 0.65 的淡化值"
  - "STRICTLY FORBIDDEN: 忽略 prefers-reduced-motion"
  - "STRICTLY FORBIDDEN: 超级专注模式仍显示任何 chrome 元素"
traceability:
  REQ-001: ["TEST-01-FOCUS-PARAGRAPH"]
  REQ-002: ["TEST-02-HEADER-AUTOHIDE"]
  REQ-003: ["TEST-03-ESC-RESTORE"]
  REQ-004: ["TEST-06-SUPER-FOCUS"]
  REQ-005: ["TEST-04-REDUCED-MOTION"]
