# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 知识导图 (FEAT-008)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-008"
  feature_name: "knowledge_mindmap"
  module: "knowledge"
  inherits_design_md: "/DESIGN.md"
  build_budget_ms: 200

design_tokens:
  css_variables:
    --mindmap-node-font: "ui-sans 13px"
    --mindmap-edge-beziers: "cubic"
    --mindmap-scale-min: "0.5"
    --mindmap-scale-max: "2.5"

component_tree:
  - component: "MindmapModal(FrostedModal)"
    layout: "Canvas (zoom/pan/select)"
    children:
      - { component: "MindmapCanvas", props: { layout: "tree-horizontal", curves: "bezier", nodeClickJumps: true } }
    states:
      empty: { title: "内容过少，暂无导图" }
      loading: { type: "skeleton-graph" }
      populated: { nodes: ["root(book)", "section", "keyword"] }

state_machine:
  mindmap:
    initial: "CLOSED"
    states:
      CLOSED: { on: { OPEN: "BUILDING" } }
      BUILDING: { on: { READY: "POPULATED", TOO_FEW: "EMPTY" } }
      POPULATED: { on: { NODE_CLICK_WITH_ANCHOR: "JUMP_AND_CLOSE", ZOOM: "POPULATED", PAN: "POPULATED", CLOSE: "CLOSED" } }
      EMPTY: { on: { CLOSE: "CLOSED" } }
      JUMP_AND_CLOSE: { on: { DONE: "CLOSED" } }

field_constraints:
  - field: "node.label"
    type: "string"
    min_length: 1
    max_length: 40
  - field: "node.level"
    type: "integer"
    allowed: [0, 1, 2]
  - field: "scale"
    type: "number"
    min: 0.5
    max: 2.5
    default: 1.0
  - field: "node_count_collapse_threshold"
    type: "integer"
    default: 40

surface_states:
  empty: { description: "内容过少 → banner + 引导，不出现空白画布" }
  loading: { description: "正在构建知识导图" }
  populated: { description: "svg 连线、节点、缩放拖拽跳转控件" }
  error: { description: "导图生成失败，重试" }

executable_tests_gherkin:
  - id: "TEST-01-BUILD-AND-RENDER"
    given: "含多章节的已解析文档"
    when: "打开知识导图"
    then: "秒级渲染「书名→章节→核心词」树布局"
  - id: "TEST-02-NODE-JUMP"
    given: "导图已展示"
    when: "点击某章节节点"
    then: "阅读区跳转对应锚点并收起导图"
  - id: "TEST-03-FALLBACK-MINIMAL"
    given: "无标题 TXT 文档"
    when: "打开导图"
    then: "以书名 + 首段核心词生成最小导图，不空白"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 生成空白画布（必须有兜底最小导图或明确空态）"
  - "STRICTLY FORBIDDEN: 阻塞主线程导致阅读卡顿（构建必须在后台）"
  - "STRICTLY FORBIDDEN: 使用彩色渐变连线/发光节点"
traceability:
  REQ-001: ["TEST-01-BUILD-AND-RENDER"]
  REQ-002: ["TEST-02-NODE-JUMP"]
  REQ-003: ["TEST-01-BUILD-AND-RENDER","TEST-02-NODE-JUMP"]
  REQ-004: ["TEST-03-FALLBACK-MINIMAL"]
