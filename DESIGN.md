---
version: 1.1.0
name: AI Reader
description: 面向长文/论文/专著深度研读者的本地优先、极简沉浸式 AI 认知阅读工作台（题材：严肃长文阅读；主职：在无干扰心流中边读边获得 AI 深度解读并沉淀批注）
colors:
  primary: "#111827"        # 正文主文本（极高对比黑灰）
  secondary: "#6B7280"      # 次级元数据 / 页码 / 引用
  tertiary: "#007AFF"       # 唯一品牌强调色（iA 电光蓝），CTA 预算 ≤3 处
  neutral: "#FAFAFA"        # 画布底色（微暖无眩光白）
  surface: "#FFFFFF"        # 阅读版心 / 卡片底色
  muted: "#9CA3AF"          # 极低对比标注 / 失焦段落
  border: "#E5E7EB"         # 1px 发丝分割线
  border-strong: "#D1D5DB"  # hover 态边框加深
  code-bg: "#F8F9FA"        # 代码块底色
  code-inline-bg: "#F3F4F6" # 行内代码底色
  highlight: "#FEF08A"      # 经典荧光笔淡黄（40% 透明）
  dark-canvas: "#121214"    # 暗色画布：深哑光碳黑
  dark-surface: "#18181B"   # 暗色表面
  dark-text: "#F4F4F5"      # 暗色正文（柔和暖白）
  dark-secondary: "#A1A1AA" # 暗色次要文本（对比度 ≥7:1）
  dark-border: "#27272A"    # 暗色发丝线
  dark-accent: "#38BDF8"    # 暗色强调（明晰天青蓝）
typography:
  reader-body:
    fontFamily: "iA Writer Duo"
    fontSize: 19px
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: -0.2px
  meta-mono:
    fontFamily: "iA Writer Mono"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
  ui-sans:
    fontFamily: "Inter"
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
rounded:
  xs: 4px    # 行内代码 / 徽标内块
  sm: 6px    # 输入框 / 标签
  md: 8px    # 按钮 / 卡片 / 图片 / 代码块
  lg: 12px   # 模态弹窗 / 抽屉 / Bottom Sheet（仅顶角）
  pill: 20px # 划词胶囊药丸
motion:
  fast: "120ms"
  base: "200ms"
  slow: "240ms"
  easing: "cubic-bezier(0.2, 0, 0, 1)"
  reduced: "0ms（prefers-reduced-motion 时全部动效归零，骨架屏改用静态 40% 灰）"
focus:
  ring: "2px solid #007AFF"
  offset: "2px"
components:
  pill-action:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.pill}"
    shadow: none
---

# DESIGN.md — AI Reader

> Agent：实现 UI 前读本文件；手艺与反 AI 皮见 Skill `frontend_craft.md`。  
> 对标来源：iA Writer 原生工作台 + 瑞士国际主义平面排版 — 已改编为阅读器场景，非品牌克隆。

## Overview

**具象物理隐喻**：一张**安静的数字排版纸**——像 iA Writer 的打字机工作台，界面在阅读时静默隐退，只在需要时精准浮现；没有工具栏森林，没有彩色卡片墙，只有纯粹的文字版心与一个电光蓝的聚焦点。

- **Audience**：深度研究者、技术极客、学者、知识工程师（严肃长文读者）。
- **Primary job of the UI**：让用户在不被打断的心流中读完一篇长文，并在遇到难点时就地获得 AI 深度解读、沉淀为可回看的批注。
- **Density**：`airy`（宽松通透；正文阅读区大量留白，控件按需浮现）。
- **Mood**：宁静、克制、纯粹、高清晰度；无装饰性渐变、无彩色阴影、无卡片堆叠、**零 emoji 功能图标**（文字即界面）。

## Colors

每色：语义名 + hex + 只用在哪里。严格单一品牌强调色 + 黑白灰高对比排版。

- **Primary** `#111827`：正文主文本、主图标。
- **Secondary** `#6B7280`：次要元数据、页码、引用。
- **Accent / Tertiary** `#007AFF`（暗色 `#38BDF8`）：唯一品牌强调色——光标蓝 / 划词胶囊触发反馈 / 唯一主 CTA。**首屏强调色预算 ≤3 处**。
- **Neutral / Surface** `#FAFAFA` 画布 / `#FFFFFF` 版心与卡片；暗色 `#121214` / `#18181B`。
- **Muted** `#9CA3AF`：失焦段落（65% 语义）与极低对比标注。
- **Border** `#E5E7EB`（hover 加深为 `#D1D5DB`）：1px 发丝分割线，全程无粗边框。
- **Semantic**：success `#1B873F` / warning `#C47D00` / error `#D9383A` / info `#007AFF`（WCAG AA 达标）。
- **对比度合规（浅色）**：正文 `#111827` on `#FAFAFA` ≈ 16:1；次要 `#6B7280` ≈ 4.8:1（≥ 4.5:1）。

### 暗色主题规则（Dark Theme Rules）

> 暗色不是"把浅色反相"：必须有独立规则，否则高亮与强调色必然走形。

| 规则 | 约束 |
|---|---|
| 画布 / 表面 | `#121214` / `#18181B`（**禁止纯黑 `#000`**，防 OLED 拖影与眩光） |
| 正文 / 次要 | `#F4F4F5` / `#A1A1AA`（**禁止纯白 `#FFF` 正文**；次要色在暗色下必须换用 `#A1A1AA`，不可沿用 `#6B7280`，后者在暗底仅 ≈3.6:1 不达标） |
| 强调色切换 | 浅色 `#007AFF` ⇄ 暗色 `#38BDF8`；两者互斥，**同一屏不得并存**；强调预算仍 ≤3 |
| 高亮标注 | 暗色禁用实心 `#FEF08A` 填充（会"挖洞"刺眼）；改用 `rgba(254,240,138,0.18)` 底色 + **左侧 2px `#38BDF8` 竖条**保证可辨识度 |
| 发丝线 | `#27272A`（暗色下 1px 视觉更弱，不得加粗补偿） |
| 代码块 | `#18181B` 底 + `#27272A` 边框；行内代码 `#27272A` 底 |
| 毛玻璃模态 | 暗色下 blur 层叠为 `rgba(18,18,20,0.72)` + `saturate(1.2)`，禁止白雾 |
| 对比度 | 暗色正文 ≥ 7:1，次要 ≥ 4.5:1 |

## Typography

### 字体家族与三端回退矩阵（Font Matrix · 实现期唯一裁决）

**决策**：仅随包分发**西文**字体（体积可控）；**CJK 一律回退系统字体**（CJK 字库 10–20MB，随包分发不可接受）。

| 角色 | 首选（随包） | Web 预览替代 | Linux 回退 | Windows 回退 | Android 回退 |
|---|---|---|---|---|---|
| 正文 Serif | `iA Writer Duo` (OFL) | `Source Serif 4` | `Noto Serif CJK SC` | `SimSun` | `Noto Serif CJK SC` |
| Mono | `iA Writer Mono` (OFL) | `JetBrains Mono` | `JetBrains Mono` / `monospace` | `Consolas` | `monospace` |
| UI Sans | `Inter` (variable) | `Inter` | `Noto Sans CJK SC` | `Microsoft YaHei` | `Noto Sans CJK SC` |

- **Reader Body**：19px / 行高 1.7 / 字距 -0.2px；西文衬线质感 + CJK 宋体回退。
- **Mono / Data**：12px——页码、字数、TTFT 指标、胶囊标签；数字列强制 `tabular-nums`。
- **UI Sans**：14px，**仅用于窗口控制与设置对话框等 chrome**，严禁用于正文。
- **Rules**：全站字体族 ≤ 3；正文版心宽度 `680px~720px`（38~45 中文字符/行）；句子大小写；大标题 `tracking-tight`。

### Markdown 内容排版规格（Content Typography · 阅读器核心施工图）

> 本产品主职是"把 Markdown 排好看"。以下为**块级/行内元素的强制样式**，渲染引擎须逐条对齐。

**标题（Heading）** — 字重与间距随层级递减，禁止彩色标题：

| 元素 | 字号 / 行高 | 字重 | 上间距 | 下间距 | 附加 |
|---|---|---|---|---|---|
| `h1` | 32px / 1.25 | 600 | 40px | 16px | `letter-spacing: -0.02em` |
| `h2` | 24px / 1.30 | 600 | 36px | 12px | `letter-spacing: -0.01em` |
| `h3` | 20px / 1.40 | 600 | 28px | 8px | — |
| `h4` ~ `h6` | 17px / 1.50 | 500 | 24px | 8px | 颜色 `secondary` |

> 标题一律 UI 字体族（Inter），与正文衬线形成层级；**禁止**标题加下划线、色块或图标前缀。

**段落 / 列表 / 引用 / 代码 / 其它**：

| 元素 | 规格 |
|---|---|
| `p` | 19px / 1.7；段间 16px；首行不缩进；中文两端不拉伸 |
| `blockquote` | 左 `2px solid #E5E7EB`；内缩 16px；17px / 1.65；色 `secondary`；上下 20px |
| `ul` | 缩进 24px；标记 `•`（`#9CA3AF`）；项间 8px |
| `ol` | 缩进 24px；序号用 mono 12px + `.`；序号列 `tabular-nums`；项间 8px |
| 任务列表 | 复选框用文本字符 `□`（未选）/ `■`（已选），**禁止**彩色 SVG 勾选框 |
| `code`（行内） | mono `0.9em`；底 `#F3F4F6`；圆角 4px；左右内边距 4px；**不加边框** |
| `pre > code`（块） | mono 13px / 1.6；底 `#F8F9FA`；1px `#E5E7EB` 边框；圆角 8px；内边距 16px；横向滚动；右上角语言标签 mono 11px `muted` |
| `hr` | 1px `#E5E7EB`；上下 32px；**禁止**装饰性图案分隔线 |
| `a` | **保持正文色** `#111827` + 下划线 1px（`text-underline-offset: 3px`）；hover 转 `accent` 并加粗下划线；外链 hover 尾部追加 `↗`；**禁止**默认蓝/紫链接色 |
| `strong` | `font-weight: 600`，**不改色** |
| `em` | 西文斜体；CJK 回退为 `font-weight: 600`（避免伪斜体） |
| `del` | 1px 中线删除线，色 `muted` |
| `table` | 1px `#E5E7EB` 全边框（无斑马纹）；表头 600 + mono 12px；行高 44px；数字列 `tabular-nums`；溢出横向滚动 |
| `img` | 版心内 `max-width: 100%`；圆角 8px；下方图注 mono 12px `muted`；上下 24px |
| 脚注 | 正文上标 mono 12px `accent`；脚注区顶部 1px 分隔 + mono 12px `secondary` |

> **绝对禁止**：为 Markdown 元素引入彩色底、卡片化、圆角气泡或 emoji 徽标。内容区永远是黑白灰 + 唯一强调色。

## Layout

- **Grid / max width**：桌面正文版心定宽居中 `700px`；书库页最大容器 `1120px`。移动端单栏满宽 + 16px 安全边距。
- **Spacing scale**：4/8 基阶（4/8/16/24/32）。
- **Section rhythm**：每屏只做一件事；顶部极简顶栏（44px）在阅读时自动隐退。
- **Hero budget**：无营销 Hero；产品即内容——首屏唯一主视觉是**正文版心**与唯一的划词胶囊 Aha 入口。

## Elevation & Depth

- **不使用投影表达层级**（界面无装饰性阴影）；层级靠**边框 / 透明度 / 高斯模糊**表达：
  - `Flat`：1px 发丝边框（胶囊、卡片）。
  - `Overlay`：毛玻璃模态（背景 σ≈14 高斯模糊 + 60/90/150 多层同色羽化光晕），入场 240ms 淡入 + 0.96→1.0 缩放。
- 例外：仅"划词胶囊"允许 0 投影（纯色药丸 + 1px 描边）。

## Shapes

- **圆角级差**：行内代码 `4px` → 输入框/标签 `6px` → 按钮/卡片/图片/代码块 `8px` → 模态/抽屉/Bottom Sheet `12px`（移动端仅顶角）→ 划词胶囊 `20px`（药丸）。**同屏圆角取值 ≤4 种**，禁止全屏同半径。

## Components

### Buttons
- **Primary**：`accent` 实心 / 文字纯白 / 8px 圆角 / 高 36px；**每屏唯一**显著主操作。
- **Secondary**：透明底 + 1px `border` / 文字 `primary`。
- **Tertiary / Ghost**：纯文字 mono 标签（如胶囊内 `[通俗]`）。
- **Destructive**：文字 `error` 红，无实心红底（克制）。

### Inputs & Forms
- Label 用 mono 12px `secondary`；聚焦 2px `accent` 外环；错误态 1px `error` 边框 + 正下方原位修复提示；禁用态 40% 不透明度 + `not-allowed`。

### Cards / Surfaces
- 仅作可交互或成组容器时使用卡片；白底/深灰底 + 1px 微边框，**无彩色背景、无投影**。卡片头部标认知模板标签（如 `[逻辑链推理 · TTFT 320ms]`），右上角 `[存为边注] [✕ 收起]`。

### Navigation
- 顶栏仅：左 `≡ 目录` / 中 文档标题（居中淡灰小字） / 右 `AI 伴读`。侧栏/抽屉以 200ms 缓动按需滑出；`Cmd/Ctrl+\` 切换左右侧栏；`Cmd/Ctrl+D` 聚焦模式；`Cmd/Ctrl+Shift+F` 超级专注。
- 导航项 ≤ 5；只链到真实存在的面板/锚点。

### 组件状态与动效契约（State & Motion Tokens · 强制）

> 任何可交互元素必须显式定义下列六态；缺失即视为未完工。

| 状态 | 规格 |
|---|---|
| `default` | 见各组件基础样式 |
| `hover` | 边框加深至 `#D1D5DB`；文字 `primary` → `accent`（仅图标/链接类）；`120ms` 过渡 |
| `active` | 底色不透明度 96% 或整体 `scale(0.99)`；`120ms` |
| `focus-visible` | `2px solid #007AFF` 外环 + `2px` 偏移；**仅键盘可见**（`:focus-visible`） |
| `disabled` | 40% 不透明度 + `cursor: not-allowed`；不响应 hover |
| `loading` | 骨架脉冲 1.8s（`cubic-bezier(.4,0,.6,1)`）或 1px 进度线；**禁止旋转 spinner 图形** |

- 动效 token：`--motion-fast 120ms` / `--motion-base 200ms` / `--motion-slow 240ms`；缓动统一 `cubic-bezier(0.2, 0, 0, 1)`。
- `prefers-reduced-motion: reduce` → 全部过渡/动画 `0ms`；骨架屏改为静态 40% 灰块；流式逐字输出改为整段淡入（`120ms`）。

## Symbol & Empty-State Language

> "文字即界面"不等于"随便找符号凑"。全局符号集合已被**封闭枚举**，越界即为违规。

| 用途 | 唯一允许的字符 | 说明 |
|---|---|---|
| 关闭 | `✕` (U+2715) | 所有弹窗/卡片/抽屉右上角统一 |
| 目录 / 菜单 | `≡` (U+2261) | 阅读区顶栏「目录」入口；仅此一处，不用于其它导航 |
| 状态 | `●` 正常 / `◐` 进行中 / `○` 未连接 / `!` 错误前缀 | 纯文本字符，禁止彩色圆点图标 |
| 列表标记 | `•` (U+2022) | 无序列表 |
| 分隔 | `|`（行内）/ `·`（元数据）/ `—`（注释与引用破折号） | |
| 外链 | `↗` (U+2197) | 仅 hover 时出现 |
| 流程箭头 | `→` (U+2192) | 步骤流转（如「划词 → 胶囊 → 伴读」），仅正文/提示文案 |
| 展开 / 折叠 | `▸` / `▾` (U+25B8 / U+25BE) | 可折叠区块、高级参数开关 |
| 任务勾选 | `□` / `■` | |
| 设计文档标注 | `※`（唯一 accent 主 CTA）/ `!`（风险与禁止项） | 仅用于 `hs_dev_docs/` 双轨线框与设计文档，不进入产品 UI |

- **空态 (Empty)**：**不使用任何图形符号与插画**。结构固定为三行——标题（18px 600）+ 引导文案（14px `secondary`）+ 主 CTA 按钮；功能相关空态可再加一个 Secondary「载入示例」。
- **加载 (Loading)**：1px 进度线或骨架块；可辅以 mono `···`，**禁止**旋转图形与百分比跳动。
- **错误 (Error)**：`!` + `error` 色标题 + 人话原因 + 原位修复动作；**禁止**堆栈、错误码裸奔、红色大图标。
- **绝对禁止**：emoji（含 Extended_Pictographic 全字符集）、颜文字、装饰性 SVG 插画、彩色状态图标、光晕特效。

## Visual Chrome & Iconography

> Chrome-first 极简：文字优先，**功能图标只承担导航/控制语义**，绝不替文案承担语义；
> **一切功能图标必须是单色单笔画几何 SVG**（MonoClip），而非 emoji 或彩色 icon font。

### 按钮样式族（统一）

| 类名 | 外形 | 用途 |
|---|---|---|
| `.btn-primary` | 高 36px，圆角 6， filled emphasis（品牌accent bg + `--on-accent` 字） | **唯一**主 CTA（每屏≤1） |
| `.btn-ghost` | 高 36px，透明底 + 1px border，hover accent border | 次要 CTA |
| `.btn-text` | 无边，文本/accent 链接；hover 下划线 | 内联轻量动作（收起/跳转/翻页） |
| `.icon-btn` | 32×32px，透明方形，单笔画图标，hover 提升 `--muted`→`--primary` | 顶栏/工具栏 icon 控件 |
| `.style-chip` | 高 26px，mono 11，圆角 4 | 高密度选项 |
| `.swatch` | 20×20 圆点，1px border | 情绪颜色选择 |

统一规则：圆角仅取 {4,6,8,12,20,50%}，gap 仅 4/8/12/16，hover 过渡 `--motion-fast`；**所有按压态（`:active`）统一** `transform: translateY(1px)`（200ms 内回弹），禁止 disparate 过渡时长。

### Iconography（单色单笔画）

- **尺寸**：16px icon 于 24px 触达尺寸（top bar）、20px icon 于 32px 范围内（标注工具栏）；**最低触达 44px** 在移动/平板上额外 padding 补足。
- **视图**：`0 0 20 20`，`viewBox` 统一；误差 ≤0.1px 对齐 pixel grid。
- **笔触**：`fill="none"`、`stroke="currentColor"`、`stroke-width="1.5"`、`stroke-linecap="round"`、`stroke-linejoin="round"`；还原按钮 hover 时 `stroke-width` 跳到 `1.75`（微强调，时长 fast）。
- **符号集合（封闭）**：除已有排版字形之外，新增 8 个 UI 控件图标，全部内嵌 SVG，**禁止 SVG 具名外链 / icon font / emoji**：

| 控件 | 名称 | 字形 / 路径描述 |
|---|---|---|
| 目录 | `toc` | 三条横线（span full→2/3） |
| 聚焦 | `focus` | 同心圆 + 中心点 |
| 伴读 | `companion` | 矩形卡片 + 右侧 speech bubble |
| 导入 | `import` | 下箭头 + 横线基座 |
| 设置 | `settings` | 三个滑动杆（值错开） |
| 标注 | `annotate` | 斜向铅笔（笔尖 + 橡皮） |
| 高亮 | `highlight` | 横 underline + 斜身 |
| AI 启动 | `invoke` | 4 条射线汇聚 |

- **aria / a11y**：所有 icon-btn **必须** `aria-label`（中文） + 可选 tooltip；点击区域不能 <32px；icon 不 carry focus ring 之外的其它视觉。
- **Anti-Slop 延伸**：`stroke-fill` 彩色 / 填充 SVG / 第三方图标库出现 = **0**；`<img src>` 嵌入 icon = 0；icon 总 bytes 0（内联 path）。

## Do's and Don'ts

**Do**
- 阅读内容是一等公民（Typography-first）；正文版心定宽、行高 1.65~1.75。
- 界面在阅读时静默隐退，需要时精准浮现（顶栏 3 秒无操作淡出）。
- 保持 100% 键盘可导航（`J/K` 翻页、`Esc` 关闭、`Cmd+K` 命令面板）。
- 伴读响应必须是确定性流式卡片，提供"一键存为边注"的无缝归档通道。
- 所有四态（Empty / Loading / Populated / Error）与六态（含 focus-visible / disabled）必须齐备。

**Don't**
- 紫靛万能渐变 / 奶油底+赤陶默认皮 / 每节 fade-up / 霓虹发光（Glow）/ 多彩标签墙。
- 正文阅读区常驻"复制/分享/收藏/打印"等次要按钮栏。
- 任何非用户触发的主动弹窗（如"AI 发现本段有重点"的主动泡泡）。
- 装饰性彩色阴影、卡片堆叠；emoji 作功能图标。
- 假数据、假证言、未证实合规口号；低对比度灰字。

## Anti-Slop 机械自检（生成后必须逐条自测，任何一条不通过即打回）

> 本清单可由脚本/正则自动执行，是"反 AI 皮"的可证伪落地，而非修辞。

| # | 检查项 | 通过条件 |
|---|---|---|
| 1 | emoji 数量 | `\p{Extended_Pictographic}` 匹配数 = **0**（白名单 `✕ ● ◐ ○ • — ↗ → ▸ ▾ □ ■ ≡` 除外——它们是无彩色变体的排版字符/几何字形，非 emoji） |
| 2 | 装饰性阴影 | **装饰性** `box-shadow`（非 `none`）出现数 = **0**；功能性阴影按白名单豁免：焦点环 `0 0 0 <n>px`（`focus-visible` / `.on` 选中态）与毛玻璃光晕（`backdrop-filter` 配套） |
| 3 | 渐变 | `linear-gradient` / `radial-gradient` 出现数 = **0** |
| 4 | 强调色预算 | 每屏 `#007AFF`（或暗色 `#38BDF8`）出现 ≤ **3**，且浅/暗强调色不并存 |
| 5 | 圆角取值 | 取值集合 ⊆ {0, 4, 6, 8, 12, 20}；同屏取值种类 ≤ **4** |
| 6 | 字体族 | 全站字体族 ≤ **3**（Serif / Mono / Sans） |
| 7 | 行宽 | 正文版心 680–720px（38–45 中文字符/行） |
| 8 | 对比度 | 正文 ≥ 7:1；次要 ≥ 4.5:1（含暗色） |
| 9 | 假内容 | `Lorem` / 假证言 / 未证实合规口号出现数 = **0** |
| 10 | 符号越界 | 出现 `Symbol & Empty-State Language` 枚举之外的符号 = **0** |
| 11 | 彩色图标 / 外部 icon 库 | **彩色 fill/stroke** 的 SVG、`<img src="…icon">`、第三方 icon font class 出现 = **0**（仅单色单笔画 MonoClip SVG，内联 path） |
| 12 | 按钮 chrome 一致 | `.btn-primary/.btn-ghost/.btn-text/.icon-btn` hover 过渡时长 ∈ {120,200}ms；`border-radius` ∈ {4,6}；`:active` 统一 `translateY(1px)`；彩色按钮 ≤ 1/屏 |

> 机械自检器：`scripts/anti_slop_check.py`（覆盖 #1/#2/#3/#5/#6/#7/#9/#10 静态项；#4 强调色预算与 #8 对比度为 **运行态** 项，在浏览器按屏实测）。任一 FAIL 即打回重做。

## Responsive Behavior

- Breakpoints：~390（Android 单栏）/ 768 / 1024 / 1440（桌面三栏）。
- 桌面：左右可折叠三栏工作台（目录 260px / 版心 700px / 伴读 440px）。
- 移动（Android）：单栏长文流 + 长按划词药丸 + 半屏 `Bottom Sheet`（下滑即关）。
- Touch targets ≥ 44px；尊重 `prefers-reduced-motion` 与 safe-area。

### Android 端特有规则（Mobile Interaction Rules）

| 规则 | 规格 |
|---|---|
| Bottom Sheet | 默认高度 **55%**；仅**顶部圆角 12px**；顶部 `36×4px` 抓握条（`#D1D5DB`）；遮罩 `rgba(17,24,39,0.32)` |
| 下滑关闭 | 下拉距离 > 30% 高度 **或** 速度 > 800px/s 触发关闭；否则回弹 200ms |
| 长按划词 | 长按 **400ms** 触发选区与胶囊，伴随 `Haptics.lightImpact` 轻反馈 |
| 系统返回手势 | 优先关闭最上层 Sheet / 模态 / 卡片；**已无浮层时才**退书库；阅读中途不静默丢失进度 |
| Safe Area | 顶部/底部 inset 各 ≥ 12px；底部追问输入框随软键盘上推，不遮挡正文 |
| 触达 | 交互目标 ≥ 44×44px，相邻目标间距 ≥ 8px |
| 滚动 | 正文滚动 60fps；顶栏 3s 无操作淡出，**下滑阅读方向**时不响应顶栏唤出 |

## Agent Prompt Guide

```text
Follow project-root DESIGN.md tokens and Do's/Don'ts.
Build the immersive reader + AI companion workbench for serious long-form readers.
One job above the fold: read the text. No AI-default aesthetic. No emoji icons. No decorative shadows or gradients.
Render Markdown with the Content Typography spec (headings / blockquote / lists / code / hr / links / tables / images).
Run the Anti-Slop Mechanical Self-Check (10 items) before considering any UI done.
```
