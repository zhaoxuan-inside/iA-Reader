# Q&A 决策日志（task_000_bootstrap_rebuild）— 第 4 轮

> 本文件为 `qa_log_003_phase0_freeze_verification.md` 的续篇，记录阶段 0 冻结前的**设计语言 refinements**（图标/动效 chrome）与 **CR-000-5**。append-only。

## 会话 / 阶段

- **日期**：2026-10-16
- **work_mode**：`DESIGN`
- **阶段**：0 产品设计（冻结前收口）
- **intent / change_size**：`BUILD` / `L`
- **拍板人**：开发者（用户）

---

## 1. 开发者新裁定（按抄录）

> 「统一所有更能按键的风格，优先使用根据产品设计语言，重新设计的 icon；尽量避免使用文字作为按钮；」

**影响面**：原型交互 chrome + 设计宪章 §Visual Chrome & Iconography + Anti-Slop 新增 #11/#12。**语义**：所有功能按压控件的视觉样式统一；图标优先于文字标签；无彩色/第三方/外链 icon，仅单色单笔画 MonoClip SVG。

## 2. 本轮落盘

### 2.1 设计宪章 `DESIGN.md` v1.1.0（§Visual Chrome & Iconography）

- 续章：4 类按钮族（`.btn-primary/.btn-ghost/.btn-text/.icon-btn`）+ `.style-chip/.swatch` 表格化定义；动效 `:active` 统一 `translateY(1px)`；gap/圆角 tokens。
- Iconography：MonoClip 规范（16px@24、20px@32、`0 0 20 20` viewBox、1.5px stroke、round caps/joins、hover 1.75px 强调、最低触达 44px）；8 个 UI 控件图标（toc/focus/companion/import/settings/annotate/highlight/invoke） enumerative closed。
- 全部 `.icon-btn` 强制 `aria-label`；Anti-Slop 延伸到彩色 SVG/icon font/外链 = 0 与笔触一致性。
- Anti-Slop 表新增 #11（彩色/外部 icon = 0）、#12（chrome 时长/半径/:active 一致性）。
- 符号枚举同时扩了 `→ ▸ ▾`（见 `CR-000-4`）。

### 2.2 原型 HTML

- top bar：3 个 `.bar-btn`（文字）→ 3 个 `.icon-btn`（MonoClip svg，`aria-label`）：TOC / Focus / Companion。
- `.bar-btn` 类被 `.icon-btn` 取代（`.bar-btn{display:none}` 保持兼容，且全部引用已移除 → 0）。
- `.btn` chrome：高度 36 / 内 padding 12 / 圆角 4 (`--r-sm`)、hover 过渡对齐、`:active` translateY(1px)、primary active scale(0.99) translateY(1px)。
- VS Code-derived `→` etc. 不作改动；所有功能 SVG 0 字节（内联 stroke 6-18 字节/图标ritz）。

### 2.3 质量

- `scripts/anti_slop_check.py` 静态 #1–#12 = **0 违规**。
- 浏览器 runtime smoke：top bar icon-btn 3/3 渲染；`.bar-btn` 0；closure 全链路（划词→胶囊→伴读→追问→存边注→标注） PASS；暗色/浅色双主题 PASS；控制台 0。
- `verify_consistency --root .`：仍 7 项遗留（旧 `backend/`，不变）。

## 3. 验证用例（-brief）

- 截图证据复现：companion 伴读卡片 `TTFT 261ms`，dark settings 暗色正常显示。
- `scripts/anti_slop_check.py` 跑在 prototype 上 ≠ any FAIL。

## 4. 遗留

- 其余 prose buttons（模板 chips / 样式 chips / 步骤文字）有意保留为文本：其语义必须由 label 承载（DESIGN.md §Iconography 红线：图标只承担导航/控制，不替文案）。
- 阶段 6 前清理 build caches（`backend/target`、`frontend/build`）。

---

## 变更请求登记（CR）

| CR | 变更 | 影响面 | 代价 | 裁定 | 落盘 |
|---|---|---|---|---|---|
| `CR-000-5` | Icon/chrome 统一：MonoClip 图标族 + `.icon-btn` + 按钮 chrome 统一 | DESIGN.md §Visual Chrome & Iconography / prototype CSS + top bar / Anti-Slop #11#12 | 低 | APPROVED | 本日志 §2 |
