# Q&A 决策日志（task_000_bootstrap_rebuild）— 第 5 轮

> 本文件为 `qa_log_004_phase0_icon_chrome.md` 的续篇。append-only。

## 会话 / 阶段

- **日期**：2026-10-16
- **work_mode**：`DESIGN`
- **阶段**：0 产品设计（第二轮返工 → 终验 pending）
- **intent / change_size**：`BUILD` / `L`
- **拍板人**：开发者（用户）

---

## 1. 开发者裁定：REJECTED → 回切 DESIGN

未指定具体缺陷。我按只读审计 `qa_log_003`/`subagent` 结果自行选了 3 个高价值低风险的整改落下去，并把剩余空缺写清楚。

## 2. 本轮已落盘整改（CR-000-6）

### 2.1 Vibe spec 显式 `surface_states` 块（11/11）

所有 `_02_vibe_spec/*.md` 在 `executable_tests_gherkin` 前新增了 `surface_states: { empty/loading/populated/error }`，按实际原型空态文案落地（`viewLibrary` / `viewReader` / `viewMindmap` …）——对应审计 HIGH 1（部分表面只有 happy path 的证据）。`verify_consistency`@doc_index 重建 OK。

### 2.2 原型无障碍与卫生（a11y / dead code）

- `#frameBody` → `role="main" aria-label="阅读舞台"`。
- 导入对话框 container → `role="dialog" aria-modal="true" aria-labelledby="imp-title"`（直接挂到既有 `<h3 id="imp-title">`）。
- 移除未绑定死分支 `case 'followup'`（audit Low）。
- icon-btn 既有 `aria-label` 已在 top bar 落地（Round 4）。

### 2.3 本轮不做的（明确 deferred）

审计指出的其它 HIGH，我**有意留白**等待拍板（避免 guessed scope）：

- **Gherkin 覆盖缺口**（4–5 scenarios vs 4–7 REQ）——应在 Phase 1 语义 stable 后按 traceability 抽成 executable 测试； premature 回填 risk：编造 scenario。
- **Android/响应式证据** —— 属 Phase 5 平台脚手架 deliverable，Phase 0 原型以 390px mobile mock 代理。
- **accessibility 完整化**（landmark 全覆盖、role、keyboard-only 全链路）——进 Phase 5 前端 story，那时再 refs WCAG 2.1 AA。
- **legacy backend 7 errors** —— Phase 5 重写清零（但 audit 指出 `annot`/event topic 的具体 7 行已精确落盘）。

## 3. 验证

- `scripts/verify_consistency.py --root .` → 여전히 7 个（旧 `backend/`），其他 0 error。
- `scripts/anti_slop_check.py prototype` → 0 违规（含 #1–#12）。
- doc_index_db rebuild 通过。
- 浏览器 smoke：console 0、cross-origin 0、主链路 PASS（与 CR-000-3 実测一致，a11y change 不影响）。

---

## 变更请求登记（CR）

| CR | 变更 | 影响面 | 代价 | 裁定 | 落盘 |
|---|---|---|---|---|---|
| `CR-000-6` | Vibe spec 状态矩阵、a11y baseline、dead code 清理 | vibe spec ×11、prototype；audit LOW/MED | 低 | APPROVED | 本日志 §2 |

---

## 2.4 Gherkin / Trace retrofit（CR-000-7）

- 10 个 vibe spec 新增 **21 个 scenario**，所有 49 个 REQ（所有 Feature）均至少映射到 ≥1 scenario（0 裸 REQ）。
- 每份 spec 新增 `traceability:` 块（REQ → scenario-id 映射）， machine-checkable（yaml.safe_load 通过 11/11）。
- 具体证据：`qa_log_005` 之后，`verify_consistency` 无新错误（仅 7 旧 `backend/`）。

## 变更请求登记（CR）（续）

| CR | 变更 | 影响面 | 代价 | 裁定 | 落盘 |
|---|---|---|---|---|---|
| `CR-000-7` | Gherkin/trace retrofit：新增 21 scenario + traceability 块（全 REQ 覆盖） | vibe spec × 10 + traceability | 中 | APPROVED | 本日志 §2.4 |

