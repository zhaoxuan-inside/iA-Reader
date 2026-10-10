# 任务计划账本：task_04_flutter_linux_packaging

- **task_id**：`task_04_flutter_linux_packaging`
- **标题**：完成 Flutter Linux 原生端构建打包与端到端/性能测试
- **change_size**：`M`
- **work_mode**：`IMPLEMENT`
- **当前阶段**：`5`
- **断点**：`S2` — 执行构建与打包
- **更新时间**：`2026-10-10T12:05:00Z`

---

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S1 | 安装 Linux 编译依赖 (clang, ninja, libgtk-3-dev) | done | 补齐 Flutter Linux 桌面编译链 |
| S2 | 执行 Flutter Linux release 构建 | done | 产出原生 bundle 与二进制 |
| S3 | 更新打包脚本并构建分发包 | done | 更新 package_dist.py，打包真实 Flutter bundle |
| S4 | 安装至系统并执行全量端到端与性能测试 | done | 执行 Flutter/Python E2E 与 Benchmark 测试，全部通过 |
| S5 | 验证门禁与归档 | done | verify_consistency.py & status COMPLETED |
