# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 书库管理与文档导入 (FEAT-001)
# Source PRD: _02_feature_spec/_01_human_prd/features/library_import_prd.md
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-001"
  feature_name: "library_import"
  module: "library"
  inherits_design_md: "/DESIGN.md"
  density: "airy"
  max_container_width: "1120px"
  primary_anchor_cta: "导入本地文档"

design_tokens:
  css_variables:
    --color-canvas: "#FAFAFA"
    --color-surface: "#FFFFFF"
    --color-text-primary: "#111827"
    --color-text-secondary: "#6B7280"
    --color-border-subtle: "#E5E7EB"
    --color-accent-focus: "#007AFF"
    --radius-md: "8px"
    --radius-lg: "12px"
  inherits: "全部继承 /DESIGN.md"

component_tree:
  - component: "LibraryScreen"
    layout: "Column(bg=canvas) — 单标题栏 + 可拖拽头部"
    slots:
      - slot: "header"
        component: "WindowControls + AppTitle(居中,淡灰小字)"
        props: { draggable: true, windowChannel: "ai.reader/window" }
      - slot: "toolbar"
        elements:
          - type: "PrimaryCTA"
            props: { label: "导入本地文档", accent: true, action: "open_file_picker" }
          - type: "TextInputSearch"
            props: { placeholder: "搜索标题…", debounceMs: 200 }
      - slot: "bookList"
        component: "BookList"
        props: { rowKey: "id", sort: "last_read_at desc" }
        columns:
          - { key: "title", title: "标题", typography: "ui-sans 15px w500" }
          - { key: "author", title: "作者", typography: "caption #6B7280" }
          - { key: "progress", title: "进度", mono: true, tabular_nums: true }
          - { key: "format", title: "格式标签", component: "MonoBadge" }
        states:
          empty: { illustration: "open_book", title: "还没有任何文档", desc: "把 Markdown 或 TXT 拖入窗口，开始沉浸阅读", cta: "导入本地文档", secondary_cta: "载入示例文章" }
          loading: { type: "skeleton", rows: 6, pulse: true }
          error: { retryAction: "refetch_library", preserveFilters: true }

state_machine:
  import_flow:
    initial: "IDLE"
    states:
      IDLE: { on: { DROP_FILES: "VALIDATING", PICK_FILES: "VALIDATING" } }
      VALIDATING:
        on:
          VALID: "HASHING"
          UNSUPPORTED_FORMAT: "REJECTED_INLINE (reason=only_md_txt)"
          TOO_LARGE_OR_EMPTY: "REJECTED_INLINE (reason=size_guard)"
      HASHING: { on: { NEW: "PARSING", DUPLICATE: "LOCATE_EXISTING" } }
      PARSING:
        on:
          OK: "PERSISTED (trigger: prepend_row, toast_success)"
          FAIL: "ROLLBACK (trigger: inline_retry)"
      PERSISTED: { on: { DONE: "IDLE" } }
      LOCATE_EXISTING: { on: { DONE: "IDLE (trigger: scroll_and_highlight)" } }
      REJECTED_INLINE: { on: { DISMISS: "IDLE" } }
      ROLLBACK: { on: { RETRY: "VALIDATING", DISMISS: "IDLE" } }

field_constraints:
  - field: "title"
    layer: "primary_screen"
    type: "string"
    required: true
    max_length: 200
    default: "derived_from_filename"
    error_message: "标题不能为空（将取自文件名）"
  - field: "format"
    layer: "primary_screen"
    type: "enum"
    allowed: ["markdown", "txt"]
    error_message: "当前版本仅支持 Markdown 与 TXT，PDF/EPUB 将在后续版本支持"
  - field: "content_bytes"
    layer: "primary_screen"
    type: "integer"
    min: 1
    max: 20971520
    error_message: "文件为空或超过 20MB，请更换文件后重试"

surface_states:
  empty: { headline: "还没有任何文档", desc: "把 Markdown 或 TXT 拖入窗口，开始沉浸式阅读与 AI 伴读", primary_cta: "导入本地文档", secondary_cta: "载入示例文章" }
  loading: { skeleton: "正在载入书库… (5 rows)", duration_hint: "< 800ms" }
  populated: { description: "库顶搜索+导入 + 列表行 (名称/元数据/格式/时间)" }
  error: { headline: "当前版本仅支持 Markdown 与 TXT", desc: "PDF/EPUB 将在后续版本支持", recovery: "重新选择文件", preserve_draft: false }

executable_tests_gherkin:
  - id: "TEST-01-IMPORT-HAPPY"
    given: "书库页已就绪"
    when: "拖入一篇合法 .md 长文"
    then: "1s 内出现在书库首行；可点击进入阅读"
  - id: "TEST-02-DUPLICATE-IDEMPOTENT"
    given: "书库已存在内容相同文档"
    when: "再次导入同内容文件"
    then: "不新增副本，滚动高亮已有条目"
  - id: "TEST-03-UNSUPPORTED-INLINE"
    given: "尝试导入 PDF/EPUB"
    when: "触发导入"
    then: "原位提示仅支持 MD/TXT；书库不变"
  - id: "TEST-04-EMPTY-FTUE"
    given: "书库为空且首次进入"
    when: "页面加载完成"
    then: "展示空态引导 + 主 CTA + 载入示例"
  - id: "TEST-05-PARSE-FAIL-ROLLBACK"
    given: "导入损坏文件"
    when: "解析抛出错误"
    then: "无半成品条目（回滚），原位提供重新导入"


  - id: "TEST-06-PROGRESS-RESTORE"
    given: "读到约 50% 后关闭窗口"
    when: "重新点书库条目打开"
    then: "滚动位置与进度百分比恢复，误差 < 1 屏"
  - id: "TEST-07-ENTRY-MANAGE"
    given: "书库条目 hover/长按"
    when: "选择重命名或移除并二次确认"
    then: "条目从列表剔除但不删源文件；重命名立即生效"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 使用 emoji 作为格式/操作图标（/DESIGN.md 红线）"
  - "STRICTLY FORBIDDEN: 导入失败时重置或清空书库其他条目"
  - "STRICTLY FORBIDDEN: 产生重复条目（必须先按内容哈希去重，幂等）"
  - "STRICTLY FORBIDDEN: 半成品记录入库（解析失败必须事务回滚）"
  - "STRICTLY FORBIDDEN: 首屏出现超过 3 处 accent 强调色"
traceability:
  REQ-001: ["TEST-01-IMPORT-HAPPY"]
  REQ-002: ["TEST-02-DUPLICATE-IDEMPOTENT"]
  REQ-003: ["TEST-03-UNSUPPORTED-INLINE"]
  REQ-004: ["TEST-04-EMPTY-FTUE"]
  REQ-005: ["TEST-06-PROGRESS-RESTORE"]
  REQ-006: ["TEST-07-ENTRY-MANAGE"]
  REQ-007: ["TEST-05-PARSE-FAIL-ROLLBACK"]
