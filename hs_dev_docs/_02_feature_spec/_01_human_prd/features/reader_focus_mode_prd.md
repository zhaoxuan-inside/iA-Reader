# 子特性需求与功能规格说明书 (Feature PRD)：聚焦模式与顶栏隐退

- **特性ID (Feature ID)**：`FEAT-003`
- **特性名称**：聚焦模式与顶栏隐退
- **所属模块**：`reader`
- **优先级**：P0
- **状态**：frozen
- **宏观品味宪章继承**：`Inherits: /DESIGN.md`
- **上级总览索引**：`_02_feature_spec/_01_human_prd/overview_prd.md`
- **关联界面原型**：`_02_feature_spec/_04_prototype_wireframe/reader_focus_mode_prototype.md`
- **面向 VibeCoding 契约**：`_02_feature_spec/_02_vibe_spec/reader_focus_mode_vibe_spec.md`

> [!NOTE]
> **微观施工图定位**：聚焦"消除视觉分散、保护阅读心流"的单点体验特性。

---

## 1. 特性洞察与核心价值界定 (Framing & Discovery)

- **现状与摩擦 (Status Quo)**：常规阅读器顶栏/侧栏/状态栏常驻，屏幕充满按钮与图标；读者用起来总有"被工具包围"的压迫感，长文连续阅读极易分神。
- **用户雇佣任务 (JTBD)**：`When` 我要专注啃一段艰深内容，`I want to` 让界面自动隐退、只聚焦当前段落，`so I can` 维持长时间心流而不被视觉噪音打断。
- **惊喜时刻 (Aha Moment)**：开启 Focus Mode 后，当前段落 100% 清晰、上下文柔和淡至 65%，**界面仿佛消失**，只剩文字（1 个快捷键即达）。
- **冷启动体验 (FTUE)**：首次阅读时顶栏在使用中自动淡出，用户无需学习即可感知"沉浸"；`Cmd/Ctrl+D` 一按即得聚焦。

---

## 2. 交互形态比选与取舍 (Approaches & Trade-offs)

| 评估维度 | 方案 A（推荐采纳） | 方案 B（备选弃用） | 取舍理由 (Trade-off Rationale) |
|---|---|---|---|
| **聚焦对象** | 段落级（当前段 100%，其余 65% 透明度） | 整行/整屏聚焦 | 段落级符合中文长文语义单元，保留可读上下文轮廓，认知负担最低 |
| **顶栏隐退** | 位置触发 + 滚动方向触发（下滚隐退、上滚唤出），3s 无操作淡出 | 常驻顶栏 / 纯悬停触发 | 纯位置接近易抖动；"滚动方向 + 计时"更稳定（防抖） |
| **超级专注** | `Cmd/Ctrl+Shift+F` 全黑/全白零元素 | 仅普通聚焦 | 提供极端沉浸选项，满足深度写作/精读 |

---

## 3. 详细字段与业务规则约束矩阵 (Specifications & Constraints)

| 字段/参数名 | 披露层级 | 类型 | 必填 | 校验规则与边界极端值 | 默认值与微文案提示 |
|---|---|---|---|---|---|
| `focus_mode` | 顶栏态 | 布尔 | 是 | true/false；随文档持久化记忆 | false |
| `focus_paragraph_index` | 内部 | 整数 | 是 | 当前聚焦段索引 ≥ 0 | 首屏首段 |
| `dim_opacity` | 内部 | 数字 | 是 | 固定 0.65（非焦段落） | 0.65 |
| `header_idle_timeout` | 内部 | 整数 | 是 | 3000ms（3s 无操作淡出） | 3000ms |
| `hyper_focus` | 快捷键态 | 布尔 | 是 | true/false；Esc 退出 | false |

### 业务分支规则矩阵
1. **分支 1（开启聚焦）**：`Cmd/Ctrl+D` 或选中段落发起伴读 → 当前段 100%，其余平滑过渡至 65%（150ms 缓动）。
2. **分支 2（退出聚焦）**：`Esc` / 双击空白 / 关闭伴读弹窗 → 全屏恢复 100% 对比度。
3. **分支 3（顶栏隐退抖动防护）**：鼠标仅在边缘位置游走而无明确上移意图时**不唤出**；仅"上滚"或"明确上移 + 停留"唤出。
4. **分支 4（超级专注）**：`Cmd/Ctrl+Shift+F` → 除正文外零元素（含零顶栏/零目录）；`Esc` 退出并恢复前态。
5. **分支 5（无障碍与减动效）**：`prefers-reduced-motion` → 淡化改为瞬时切换，避免动画引发不适。

---

## 4. 需求原子分解与行为驱动验收标准 (Requirements & Functional DoD)

### 4.1 核心需求原子分解清单 (Atomic Requirements Matrix)
| 需求编号 | 需求名称与规则简述 | 关联字段/动作 | 验收物理证据 | 优先级 |
|---|---|---|---|---|
| `REQ-001` | 段落级聚焦（100% / 65%） | 快捷键或选中段落 | 当前段清晰、其余段透明度 0.65，150ms 内完成过渡 | P0 |
| `REQ-002` | 顶栏自动隐退（3s 无操作）与滚动方向唤出 | 滚动/停驻 | 下滚隐退，上滚/明确上移唤出，无抖动 | P0 |
| `REQ-003` | `Esc` 退出聚焦并恢复 100% 对比度 | 按下 Esc | 全屏 100ms 内恢复 | P0 |
| `REQ-004` | 超级专注模式（零 chrome） | `Cmd/Ctrl+Shift+F` | 除正文外零元素，Esc 退出 | P1 |
| `REQ-005` | 减动效与无障碍回退 | 系统 reduced-motion | 淡化改瞬时切换，无闪烁 | P1 |

### 4.2 行为驱动产品验收场景 (Gherkin Scenarios)

```gherkin
Feature: 聚焦模式与顶栏隐退

  Scenario: REQ-001 开启段落级聚焦 (Happy Path)
    Given 用户正在阅读一篇包含多个段落的文档
    When 用户按下 Cmd/Ctrl+D 或选中某段落发起伴读
    Then 当前段落保持 100% 对比度
    And 其余段落平滑淡化至 65% 透明度（150ms 过渡）

  Scenario: REQ-002 顶栏滚动方向隐退与唤出 (Happy Path)
    Given 顶栏当前可见
    When 用户向下滚动阅读超过一定阈值
    Then 顶栏平滑淡出
    And 当用户向上滚动或指针明确上移至边缘并停留时，顶栏重新淡入

  Scenario: REQ-003 Esc 退出聚焦 (Validation)
    Given 当前处于聚焦模式
    When 用户按下 Esc 键
    Then 全屏在 100ms 内恢复 100% 对比度

  Scenario: REQ-005 减动效回退 (Accessibility)
    Given 系统开启了 prefers-reduced-motion
    When 用户切换聚焦或顶栏显隐
    Then 淡化以瞬时切换方式生效，不产生动画
```
