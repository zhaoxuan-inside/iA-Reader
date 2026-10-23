# Q&A 决策日志（task_000_bootstrap_rebuild）

> 审讯 / 开场确认 / 变更裁定的一切问答与拍板记录，供跨会话回溯与返工溯源。每轮追加，不覆盖旧记录。

## 会话 / 阶段

- **日期**：2026-10-16
- **work_mode**：`DESIGN`
- **阶段**：0 产品设计（开场确认 + 产品设计沟通 / MVP 范围裁定）
- **intent / change_size**：`BUILD` / `L`
- **拍板人**：开发者（用户）

---

## 0. 开场确认（opening_alignment O1～O4）

### O1 需求复述（已确认）

- **做什么**：使用 `hs-dev-skill` 对 `ai-reader`（AI Reader 沉浸式 AI 认知阅读器）进行**从零重写（BUILD, L 满配 0→6）**，产出**可运行产品 + 完整文档体系**。
- **为谁**：深度研究者 / 技术极客 / 严肃读者（本地优先、离线沉淀知识）。
- **边界**：仅重写本产品；本期不新增超出原 PRD 的产品功能；坚持 Local-First 零网络依赖做基础能力。
- **关键动词**：重新构建（代码）、重新校准（文档体系）、闭环验收（测试全绿 + 门禁）。

### O2 假设与空白清单（已闭合）

| 编号 | 空白/决策点 | 裁定 |
|---|---|---|
| Q-A | 「重新完整开发」的模式 | 开发者确认：**从零重写（BUILD, L）** |
| Q-B | 现有代码处置边界 | 开发者确认：**允许推倒重写部分模块**（默认沿用可用实现，问题模块可整体重写） |
| Q-C | 最终交付形态 | 开发者确认：**可运行产品 + 完整文档体系** |

### O3 约束与干系人

- 技术栈固定：Flutter 多端 + Rust C-ABI FFI 核心引擎 + SQLite/WAL。
- 设计语言：iA Writer 极简主义（已冻结，收敛入根 `DESIGN.md`）。
- 治理：默认轻量（无 CI/CD、无可观测性、无容灾）；保留版本控制 / 环境机密 / 供应链 / 隐私 / Agent 护栏基线。
- 当前版本：`v0.0.5` → 重建后按四段式版本号体系演进。

### O4 分级建议（已确认）

- `intent=BUILD`，`change_size=L`，`work_mode=DESIGN`。

---

## 1. 问题与答复（产品设计沟通 / 审讯）

### Q1. 单一核心假设（Single Risky Assumption）

- **题域**：产品语义 / 范围裁剪
- **题干**：本产品只保留一个功能还能成立，那个功能是什么？
- **选项与利弊**：
  - A：**本地解析长文 → 划词 → AI 认知伴读流式返回 → 一键存为边注**（推荐：构成"读懂长文"的最小价值闭环）
  - B：仅本地解析与沉浸阅读（无 AI）
- **开发者答复**：默认采纳 A（伴随后续 MVP 裁定一并生效）
- **采纳决策**：核心假设 = **A**。
- **关联落盘**：`overview_prd.md` / `ai_reader_phased_plan.md`

### Q2. CEO 质疑式裁剪（The Radical Cut · 开发者最终裁定）

- **题域**：范围裁剪
- **题干**：Agent 站在严苛 CEO 视角对辅助特性发起质疑，请开发者逐项裁定是否裁出 MVP。
- **Agent 质疑清单与建议**：

  | 编号 | 拟裁剪项 | 质疑理由 | Agent 建议 |
  |---|---|---|---|
  | C1 | 知识导图 + 权重词云 | 核心闭环（读+伴读）不依赖图形化知识图谱 | 降级 Phase 2 |
  | C2 | 独立 AI 键盘面板（Cmd+K） | 划词胶囊已直达四模板，快捷键面板为效率增强 | 降级 Phase 2 |
  | C3 | 移动端（iOS/Android）+ Bottom Sheet | 多端适配成本高，先用桌面验证核心假设 | 降级 Phase 2 |
  | C4 | 标注 7 样式 × 调色板 | 高亮 + 边注即可验证批注闭环 | 收敛为高亮 + 边注 |
  | C5 | PDF / EPUB 解析 | 复杂排版解析成本高、易错 | MVP 仅 Markdown + TXT |

- **开发者答复（最终裁定）**：
  - **C5 → 采纳裁剪**：MVP **仅支持 Markdown + TXT** 解析；PDF/EPUB 降级 **Phase 2**。
  - **C1/C2/C4 → 不裁剪**：知识导图/词云、独立 AI 键盘面板、标注多（7）样式 × 调色板 **保留在 MVP**。
  - **C3 → 部分裁剪（平台口径）**：**移动端保留 Android，暂缓 iOS**；**桌面端保留 Linux + Windows，暂缓 macOS**。即 MVP 目标平台 = **Linux + Windows + Android**。
- **采纳决策**：MVP 范围 = 除 PDF/EPUB 外的全部既有功能；平台 = Linux + Windows + Android。
- **关联落盘**：`ai_reader_phased_plan.md`（MoSCoW 矩阵）/ `overview_prd.md`

> **No Admin in MVP**：本产品为本地单用户桌面/移动应用，无后台/多角色/计费/权限体系，天然无管理台。

### Q3. 团队胃口与时间箱（Appetite）

- **题域**：范围裁剪 / 排期
- **题干**：本次 MVP 期望的时间箱？
- **选项**：A：1~3 天极速验证；B：1~2 周首发；C：**不设时间箱，质量优先做到底**
- **开发者答复**：**C**。
- **采纳决策**：不设硬性时间箱；以"质量优先、测试全绿、门禁通过"为唯一准出标准；断路器原则仍适用于范围（工期压力下优先砍 Phase 2 项）。

### Q4. 阶段首日垂直切片与交付平台（Tracer Bullet & Platform）

- **题域**：对外契约 / 交付形态
- **题干**：MVP 首个垂直贯穿切片与主交付平台？
- **选项**：A：Linux 桌面单端；B：桌面三端；C：全平台五端
- **开发者答复**：自定义 → **linux + windows + android**。
- **采纳决策**：
  - **主交付平台 = Linux + Windows + Android**（iOS、macOS 顺延 Phase 2）。
  - **Day 1 垂直曳光弹切片** = `导入 Markdown/TXT → Rust 引擎解析入库(SQLite) → 桌面阅读器渲染 → 划词 → 伴读流式卡片 → 存为边注`，首日跑通端到端冒烟。

### Q5. DB 设计决策（硬闸门）

- **题域**：DB 设计
- **题干**：本产品触及 SQLite 表族设计（books/sections/sentences/keywords/keyword_relations/mindmap_nodes/annotations/conversations 等），是否授权按阶段 3 设计稿落地？
- **开发者答复**：**授权：按设计稿建表**（含标准审计字段 `id/created_at/updated_at/description/is_del/version`）。
- **采纳决策**：阶段 3 输出的 DDL + V/U 迁移经本授权即可落地编码；后续任何新增/破坏性表变更仍需再次开发者决策。
- **关联落盘**：`_04_engineering_contract/_01_db_schema/`

---

## 变更请求登记（CR）

| CR 编号 | 变更描述 | 影响面 | 返工代价 | 开发者裁定 | 落盘 |
|---|---|---|---|---|---|
| `CR-000-1` | 从零重写（BUILD, L）替代既有 v2.4 文档体系 | 全工程 | 高 | APPROVED | 本日志 §0 |
| `CR-000-2` | MVP 裁剪 PDF/EPUB；平台收敛 Linux/Win/Android | 解析引擎/多端构建 | 中 | APPROVED | `ai_reader_phased_plan.md` |
