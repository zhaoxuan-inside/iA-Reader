# 任务详细设计与执行记录：task_18_deb_metadata

- **任务名称**：清零遗留③：deb 打包元数据修正（Depends/Description 对齐 Flutter 桌面应用）
- **变更分级**：`M`
- **当前状态**：`READY`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T10:18:23Z`
- **最后更新**：`2026-10-11T10:18:23Z`

---

## 1. 任务背景与目标
暂无详细背景描述

---

## 2. 验收标准
1. 单元测试覆盖率达标\n2. 契约比对一致

---

## 3. 执行步骤 (Checklist)
- [ ] 1. 完善设计文档与接口定义
- [ ] 2. 同步 DB 迁移脚本（V/U）
- [ ] 3. 编写/修改核心六元组业务逻辑
- [ ] 4. 编写全覆盖单测与契约测试
- [ ] 5. 本地质量门禁与提交前自检

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
(待更新)
```

---

## 5. 验证与门禁记录
- 单测覆盖率：`0%`
- 契约比对：`PENDING`
# 任务详细设计与执行记录：task_18_deb_metadata

- **任务名称**：清零遗留③——deb 打包元数据修正
- **变更分级**：`S`
- **当前状态**：`COMPLETED`
- **优先级**：P2
- **负责人**：agent
- **开始时间**：`2026-10-11T20:05:00Z`

---

## 1. 任务背景与目标

deb control 是旧架构（Python CLI 时代）遗留：`Depends: python3` 且 Description 为 "Headless Core ... CLI"，与现装 Flutter 桌面应用不符。

## 2. 变更内容

- `Depends`: `python3, libc6` → `libc6, libgtk-3-0, libstdc++6`（Flutter Linux GTK 运行时真实依赖）
- `Description`: 重写为 Flutter 桌面客户端 + Rust 核心引擎的准确描述（标注系统/流式伴读/AI 键盘/导图词云/集中存储）
- `Version`: 0.0.5 → 0.0.6（伴随 task_12~17 功能迭代）
- `output/build_deb/DEBIAN/control` 构建产物目录同步（脚本每次 rm -rf 重建，模板为唯一事实源）

## 3. 验证

- 下次打包以模板为准；.desktop 文件核对无遗留（Exec/Icon/MimeType 正确）。
