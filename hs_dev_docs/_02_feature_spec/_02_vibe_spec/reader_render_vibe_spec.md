# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 结构化解析与版心阅读渲染 (FEAT-002)
# Source PRD: _02_feature_spec/_01_human_prd/features/reader_render_prd.md
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-002"
  feature_name: "reader_render"
  module: "reader"
  inherits_design_md: "/DESIGN.md"
  density: "airy"
  reading_column_width: "700px"
  primary_anchor_cta: "(无显式 CTA — 正文即主视觉)"

design_tokens:
  css_variables:
    --reader-font-family: "iA Writer Duo, Source Han Serif SC, serif"
    --reader-font-size: "19px"
    --reader-line-height: "1.7"
    --reader-letter-spacing: "-0.2px"
    --reader-column-max: "700px"
    --paragraph-gap: "1.2em"
    --meta-font: "iA Writer Mono 12px"

component_tree:
  - component: "ReaderScreen"
    layout: "Stack[ FocusModeDimLayer, Column[ Header(autohide), Row[ TocTree, ReadingColumn, CompanionSlot ] ] ]"
    slots:
      - slot: "header"
        component: "MinimalChromeHeader"
        props: { height: "44px", title: "文档标题(居中淡灰)", autohide: true, windowControls: true }
      - slot: "toc"
        component: "TocTree"
        props: { width: "260px", collapsible: true, levels: "H1..H6", activeHighlight: true }
      - slot: "readingColumn"
        component: "VirtualizedReadingColumn"
        props: { maxWidth: "700px", font: "iA Writer Duo 19/1.7", lazyChunk: true }
        blocks: ["heading", "paragraph", "list", "blockquote", "code", "emphasis"]
      - slot: "companionSlot"
        component: "CompanionModalSlot"
        props: { width: "440px" }
    states:
      empty: { text: "文档内容为空" }
      loading: { type: "skeleton", blocks: 6 }
      error: { retryAction: "reload_document" }

state_machine:
  render:
    initial: "PARSE_PENDING"
    states:
      PARSE_PENDING: { on: { AST_READY: "RENDER_FIRST_SCREEN", PARSE_FAIL: "DEGRADED" } }
      RENDER_FIRST_SCREEN: { on: { SCROLL: "LAZY_LOAD", EOF: "IDLE" } }
      LAZY_LOAD: { on: { CHUNK_APPENDED: "RENDER_FIRST_SCREEN" } }
      DEGRADED: { on: { RETRY: "PARSE_PENDING" } }
      IDLE: { on: { SCROLL: "LAZY_LOAD" } }

field_constraints:
  - field: "section.level"
    type: "integer"
    min: 1
    max: 6
  - field: "paragraph.index"
    type: "integer"
    min: 0
    unique: true
  - field: "char_offset"
    type: "integer"
    min: 0
  - field: "first_screen_budget_ms"
    type: "integer"
    max: 1500

surface_states:
  empty: { headline: "该文档内容为空", desc: "请返回书库导入包含正文的 Markdown 或 TXT 文档", primary_cta: "返回书库" }
  loading: { skeleton: "正在解析文档… (6 rows)", duration_hint: "Markdown 10 万字 < 1.5s" }
  populated: { description: "700px 版心 + h1-h4 + ol/ul + code + table + figure + blockquote (DESIGN.md §D7)" }
  error: { headline: "该文档部分语法无法完整解析", desc: "已按纯文本降级渲染，阅读不受影响", recovery: "重新解析", preserve_draft: true }

executable_tests_gherkin:
  - id: "TEST-01-RENDER-TYPOGRAPHY"
    given: "文档已解析"
    when: "打开文档"
    then: "正文定宽 700px 居中，字体 iA Writer Duo 19px/行高 1.7"
  - id: "TEST-02-TOC-ANCHOR"
    given: "文档含多章节"
    when: "点击目录项"
    then: "平滑滚动到对应标题锚点，目录项高亮"
  - id: "TEST-03-LAZY-PERF"
    given: "约 10 万字文档"
    when: "打开文档"
    then: "1.5s 内首屏可读；滚动 60fps"
  - id: "TEST-04-MALFORMED-DEGRADE"
    given: "含未闭合代码块的文档"
    when: "打开文档"
    then: "尽力渲染为段落，不崩溃、不空白"


  - id: "TEST-05-PROGRESS-PERSIST"
    given: "阅读时滚动 > 1 屏后关闭"
    when: "重新打开文档"
    then: "进度恢复至上滚位置（误差 < 1 屏）"
  - id: "TEST-07-ANCHOR-STABILITY"
    given: "打开文档并缩放/调整窗口"
    when: "完成重排"
    then: "段落锚点校准正确，划词定位不漂移"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 使用 WebView 富文本渲染（必须结构化 AST）"
  - "STRICTLY FORBIDDEN: 正文版心宽度偏离 680–720px 区间"
  - "STRICTLY FORBIDDEN: 解析失败导致白屏（必须降级为纯文本段落）"
  - "STRICTLY FORBIDDEN: 段落/句子锚点缺失（划词/标注依赖其稳定）"
traceability:
  REQ-001: ["TEST-01-RENDER-TYPOGRAPHY"]
  REQ-002: ["TEST-01-RENDER-TYPOGRAPHY","TEST-02-TOC-ANCHOR"]
  REQ-003: ["TEST-02-TOC-ANCHOR"]
  REQ-004: ["TEST-03-LAZY-PERF","TEST-07-ANCHOR-STABILITY"]
  REQ-005: ["TEST-05-PROGRESS-PERSIST"]
  REQ-006: ["TEST-04-MALFORMED-DEGRADE"]
  REQ-007: ["TEST-07-ANCHOR-STABILITY"]
