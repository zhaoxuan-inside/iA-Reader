# ==============================================================================
# VIBECODING EXECUTION SPEC (Machine-Actionable Contract)
# Target Feature: 多维标注与边注管理 (FEAT-007)
# Macro Taste Charter: Inherits /DESIGN.md
# ==============================================================================

meta:
  feature_id: "FEAT-007"
  feature_name: "annotation_styles"
  module: "annotation"
  inherits_design_md: "/DESIGN.md"

design_tokens:
  css_variables:
    --hl-yellow: "#FEF08A"
    --hl-green: "#BBF7D0"
    --hl-blue: "#BFDBFE"
    --hl-pink: "#FBCFE8"
    --hl-purple: "#E9D5FF"
    --hl-orange: "#FED7AA"
    --anno-panel-width: "360px"

component_tree:
  - component: "AnnotationPalette"
    props: { anchoredToSelection: true }
    children:
      - { component: "StylePicker", options: ["下划线", "波浪线", "加粗", "斜体", "删除线", "半高亮", "高亮"] }
      - { component: "ColorSwatch", options: ["yellow", "green", "blue", "pink", "purple", "orange"] }
  - component: "NoteEditorPopover"
    children: [{ component: "TextArea", field: "note_body", placeholder: "写点什么…" }]
  - component: "AnnotationManager(FrostedModal)"
    props: { width: "360px" }
    columns: ["样式预览", "原文摘要", "边注摘要", "来源", "操作(定位/编辑/删除)"]
    states:
      empty: { title: "还没有标注", desc: "划选文本即可创建标注或边注" }
      populated: { list: "annotations" }

state_machine:
  annotation:
    initial: "NONE"
    states:
      NONE: { on: { SELECTION: "PALETTE_OPEN" } }
      PALETTE_OPEN:
        on:
          PICK_STYLE_COLOR: "PERSISTING"
          ADD_NOTE: "NOTE_EDITING"
          CANCEL: "NONE"
      NOTE_EDITING: { on: { SAVE: "PERSISTING", CANCEL: "PALETTE_OPEN" } }
      PERSISTING: { on: { OK: "NONE (render_inline)", FAIL: "PALETTE_OPEN (inline_error, keep_inputs)" } }
  manage:
    initial: "CLOSED"
    states:
      CLOSED: { on: { OPEN: "LIST" } }
      LIST: { on: { LOCATE: "LIST (jump_anchor)", EDIT: "EDIT", DELETE: "CONFIRM_DELETE" } }
      EDIT: { on: { SAVED: "LIST", CANCEL: "LIST" } }
      CONFIRM_DELETE: { on: { CONFIRM: "LIST (soft_delete)", CANCEL: "LIST" } }

field_constraints:
  - field: "style"
    type: "enum"
    required: true
    allowed: ["highlight", "semi_highlight", "underline", "wavy", "bold", "italic", "strike"]
    default: "highlight"
  - field: "color"
    type: "enum"
    required: true
    allowed: ["yellow", "green", "blue", "pink", "purple", "orange"]
    default: "yellow"
  - field: "note_body"
    type: "string"
    required: false
    max_length: 2000
    placeholder: "写点什么…"
  - field: "origin"
    type: "enum"
    allowed: ["manual", "companion"]

surface_states:
  empty: { headline: "还没有任何标注", desc: "拖选正文后选择样式或存为边注，标注会出现在这里", primary_cta: "返回正文" }
  loading: { skeleton: "正在载入标注… (4 skeleton rows)", duration_hint: "< 800ms" }
  populated: { description: "样式条 + 颜色板 + 标注列表 (style/tag/note/owner)，7 样式 × 6 颜色" }
  error: { headline: "标注载入失败", desc: "本地数据库读取异常", recovery: "重试", preserve_draft: true }

executable_tests_gherkin:
  - id: "TEST-01-CREATE-STYLE-COLOR"
    given: "已选中文本"
    when: "选择「下划线 + 蓝色」"
    then: "正文即时以内联下划蓝呈现，锚点精确"
  - id: "TEST-02-COMPANION-NOTE-IDEMPOTENT"
    given: "伴读卡片有内容"
    when: "点击「存为边注」两次"
    then: "生成一条 origin=companion 边注；二次幂等"
  - id: "TEST-03-EDIT-NOTE-PERSIST"
    given: "已有边注"
    when: "编辑并保存"
    then: "重开文档边注与锚点保持正确"
  - id: "TEST-04-OVERLAP-CLEAN"
    given: "某段已有高亮"
    when: "对重叠区新建下划线"
    then: "重叠区以最新样式覆盖，无脏区间"


  - id: "TEST-05-LIST-JUMP"
    given: "已创建 ≥ 1 条标注"
    when: "点击标注面板中的某条列表项"
    then: "正文视图平滑滚动至该标注锚点，brief 高亮 confirm"
  - id: "TEST-06-SOFT-DELETE-UNDO"
    given: "列表中选中一条标注"
    when: "点删除并确认"
    then: "软删除并出现 5 秒撤销窗口；撤销后条目恢复"

hard_guardrails:
  - "STRICTLY FORBIDDEN: 产生重叠/错位脏区间或悬空锚点"
  - "STRICTLY FORBIDDEN: 删除不经二次确认（软删除 is_del）"
  - "STRICTLY FORBIDDEN: 物理删除用户边注内容（软删除可恢复）"
  - "STRICTLY FORBIDDEN: 领域事件使用命令式命名（必须 .created/.updated/.deleted 过去分词）"
  - "STRICTLY FORBIDDEN: 使用 emoji 作为样式图标"
traceability:
  REQ-001: ["TEST-01-CREATE-STYLE-COLOR"]
  REQ-002: ["TEST-03-EDIT-NOTE-PERSIST"]
  REQ-003: ["TEST-02-COMPANION-NOTE-IDEMPOTENT"]
  REQ-004: ["TEST-05-LIST-JUMP"]
  REQ-005: ["TEST-04-OVERLAP-CLEAN"]
  REQ-006: ["TEST-06-SOFT-DELETE-UNDO"]
