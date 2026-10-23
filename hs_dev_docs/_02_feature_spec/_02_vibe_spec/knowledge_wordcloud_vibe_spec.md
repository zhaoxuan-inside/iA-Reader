# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 关键词词云 (FEAT-009)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-009"
  feature_name: "knowledge_wordcloud"
  module: "knowledge"
  inherits_design_md: "/DESIGN.md"

design_tokens:
  css_variables:
    --wordcloud-font-min: "14px"
    --wordcloud-font-max: "48px"
    --wordcloud-color-primary: "#111827"
    --wordcloud-color-secondary: "#6B7280"

component_tree:
  - component: "WordCloudModal(FrostedModal)"
    children:
      - { component: "ScopeToggle", options: ["全文", "本章"] }
      - { component: "WordCloud", props: { fontScale: "weight->[14,48]", hoverShowsWeight: true, clickJumps: true } }
    states:
      empty: { title: "内容过少，暂无词云" }
      populated: { terms: "weighted" }

state_machine:
  wordcloud:
    initial: "CLOSED"
    states:
      CLOSED: { on: { OPEN: "BUILDING" } }
      BUILDING: { on: { READY: "POPULATED", TOO_FEW: "EMPTY" } }
      POPULATED: { on: { SWITCH_SCOPE: "BUILDING", WORD_CLICK: "JUMP", CLOSE: "CLOSED" } }
      EMPTY: { on: { CLOSE: "CLOSED" } }
      JUMP: { on: { DONE: "POPULATED" } }

field_constraints:
  - field: "term"
    type: "string"
    min_length: 1
    max_length: 20
  - field: "weight"
    type: "number"
    min: 0.0
    max: 1.0
  - field: "scope"
    type: "enum"
    allowed: ["full", "section"]
    default: "full"
  - field: "min_terms_threshold"
    type: "integer"
    default: 8

surface_states:
  empty: { headline: "内容过少，暂无词云", desc: "该文档关键词数量不足" }
  loading: { skeleton: "正在计算关键词权重… (4 rows)", duration_hint: "< 1500ms" }
  populated: { description: "字号=权重的词云 + 全文/本章切换 + 悬停权重" }
  error: { headline: "词云生成失败", desc: "请返回阅读后重试", recovery: "重试", preserve_draft: true }

executable_tests_gherkin:
  - id: "TEST-01-RENDER-WEIGHTED"
    given: "内容充足的已解析文档"
    when: "打开词云"
    then: "秒级渲染；字号与权重正相关"
  - id: "TEST-02-JUMP"
    given: "词云已展示"
    when: "点击关键词"
    then: "阅读区定位到该词相关段落锚点"
  - id: "TEST-03-EMPTY"
    given: "极短文档"
    when: "打开词云"
    then: "展示「内容过少，暂无词云」明确空态"


  - id: "TEST-04-SCOPE-SWITCH"
    given: "词云展示全文权重"
    when: "切换至\"本章\""
    then: "按章节范围重算并重绘，字号反映新权重"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 使用彩色随机配色/旋转词云（克制配色，字号表达权重）"
  - "STRICTLY FORBIDDEN: 空白画布（必须空态提示）"
  - "STRICTLY FORBIDDEN: 主线程阻塞计算（后台离线计算）"
traceability:
  REQ-001: ["TEST-01-RENDER-WEIGHTED"]
  REQ-002: ["TEST-04-SCOPE-SWITCH"]
  REQ-003: ["TEST-02-JUMP"]
  REQ-004: ["TEST-03-EMPTY","TEST-04-SCOPE-SWITCH"]
