# 任务计划账本：task_000_bootstrap_rebuild

- **task_id**：`task_000_bootstrap_rebuild`
- **标题**：AI Reader 从零重写重建（BUILD / L 满配 0→6）
- **change_size**：`L`
- **work_mode**：`DESIGN`
- **当前阶段**：`0`
- **断点**：`S0` — 阶段 0 冻结签收单 v1.1 待开发者签署 APPROVED（返工终验已通过，见 qa_log_003）
- **更新时间**：`2026-10-16T01:36:00Z`

---

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S0 | 阶段 0 产品设计（开场确认 + 审讯 + MVP 裁定 + 品味宪章 + 一源双视图 + 双轨原型 + 规划书 + 冻结签收） | doing | 产物齐备；返工 P1–P6/D1–D7 全量整改 + 终验通过（qa_log_002/003）；待开发者签署 `phase0_freeze_signoff.md` |
| S1 | 阶段 1 技术选型 ADR（Flutter + Rust FFI + SQLite/WAL，顶置 [VIBE_CONTRACT]，附选型拍板单） | pending | |
| S2 | 阶段 2 架构设计（dev_paradigm + 模块边界 + 深模块词汇 + 模式集群 + 顶置契约） | pending | |
| S3 | 阶段 3 工程四要素（DB DDL + V/U 迁移 / FFI 接口契约 / 六元组方法设计 / 调用链） | pending | DB 已获开发者授权，按设计稿落地 |
| S4 | 阶段 4 任务分解 + context pack 编译装配 + seam 识别 | pending | |
| S5 | 阶段 5 垂直切片 TDD 实现（复用 backend Rust + frontend Flutter，新增 Windows/Android 平台脚手架） | pending | |
| S6 | 阶段 6 质量门禁（make test 全绿 + 静态零告警 + verify_consistency --strict）+ 归档 + 本地 Commit | pending | |
