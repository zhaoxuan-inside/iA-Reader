# 子特性需求与功能规格说明书 (Feature PRD)：独立 AI 键盘面板

- **特性ID (Feature ID)**：`FEAT-010`
- **特性名称**：独立 AI 键盘面板
- **所属模块**：`assistant`
- **优先级**：P1
- **状态**：frozen
- **宏观品味宪章继承**：`Inherits: /DESIGN.md`
- **上级总览索引**：`_02_feature_spec/_01_human_prd/overview_prd.md`
- **关联界面原型**：`_02_feature_spec/_04_prototype_wireframe/assistant_keyboard_prototype.md`
- **面向 VibeCoding 契约**：`_02_feature_spec/_02_vibe_spec/assistant_keyboard_vibe_spec.md`

> [!NOTE]
> **微观施工图定位**：以键盘驱动的方式复用四认知模板，服务于重度键盘用户的高效操作。

---

## 1. 特性洞察与核心价值界定 (Framing & Discovery)

- **现状与摩擦 (Status Quo)**：重度用户习惯键鼠之外的纯键盘操作，但划词胶囊需要鼠标划选；缺少一个"不用离开键盘就能发起 AI 动作"的通道。
- **用户雇佣任务 (JTBD)**：`When` 我在键盘操作流中，`I want to` 用 `Cmd/Ctrl+K` 唤起一个分类模板面板并对当前作用域发起动作，`so I can` 不碰鼠标地完成伴读/摘要。
- **惊喜时刻 (Aha Moment)**：`Cmd+K` → 底部停靠面板浮现 → 键帽模板网格 + 当前作用域提示，回车即执行。
- **冷启动体验 (FTUE)**：面板首次打开即显示分类与作用域说明；无选区时提示"未选中文本，将对当前段落执行"。

---

## 2. 交互形态比选与取舍 (Approaches & Trade-offs)

| 评估维度 | 方案 A（推荐采纳） | 方案 B（备选弃用） | 取舍理由 (Trade-off Rationale) |
|---|---|---|---|
| **形态** | 底部停靠面板（键帽模板网格） | 居中命令面板（纯文本列表） | 底部停靠不遮挡正文上半，键帽网格更利于键位记忆 |
| **作用域解析** | 选中→选区；无选中→当前段落（回退） | 仅选区 | 键盘流中常无选中，回退到当前段落保证可用 |
| **唤起** | `Cmd/Ctrl+K` | 仅按钮 | 键盘优先，无止境鼠标依赖 |

---

## 3. 详细字段与业务规则约束矩阵 (Specifications & Constraints)

| 字段/参数名 | 披露层级 | 类型 | 必填 | 校验规则与边界极端值 | 默认值与微文案提示 |
|---|---|---|---|---|---|
| `scope` | 面板首屏 | 枚举 | 是 | `selection`/`paragraph`/`document` | 自动解析 |
| `template` | 键帽网格 | 枚举 | 是 | `general`/`logic`/`critical`/`term`/`summarize` | 无 |
| `key_hint` | 键帽 | 字符串 | 是 | 如 `1`–`5` 快捷键位 | — |
| `panel_visible` | 内部 | 布尔 | 是 | true/false；Esc 关闭 | false |

### 业务分支规则矩阵
1. **分支 1（唤起）**：`Cmd/Ctrl+K` → 面板滑入，自动解析作用域并展示提示。
2. **分支 2（执行）**：选模板 → 复用 FEAT-005 伴读流；作用域为选区/段落/全文。
3. **分支 3（无选区回退）**：作用域回退当前焦点段落，并在面板顶部提示。
4. **分支 4（数字键选择）**：按 `1`–`5` 快速执行对应模板。
5. **分支 5（关闭）**：`Esc` 或点击外部关闭，不改动正文。

---

## 4. 需求原子分解与行为驱动验收标准 (Requirements & Functional DoD)

### 4.1 核心需求原子分解清单 (Atomic Requirements Matrix)
| 需求编号 | 需求名称与规则简述 | 关联字段/动作 | 验收物理证据 | 优先级 |
|---|---|---|---|---|
| `REQ-001` | `Cmd/Ctrl+K` 唤起底部面板 | 快捷键 | 面板滑入，键帽网格可见 | P0 |
| `REQ-002` | 自动解析作用域并提示回退 | 打开面板 | 顶部明示当前作用域（选区/段落/全文） | P0 |
| `REQ-003` | 键帽执行复用四模板 + 摘要 | 点击/数字键 | 触发对应伴读流 | P1 |
| `REQ-004` | Esc/外部点击关闭 | 关闭 | 面板收起，正文不变 | P1 |

### 4.2 行为驱动产品验收场景 (Gherkin Scenarios)

```gherkin
Feature: 独立 AI 键盘面板

  Scenario: REQ-001/002 唤起面板并解析作用域 (Happy Path)
    Given 用户正在阅读文档且未选中文本
    When 用户按下 Cmd/Ctrl+K
    Then 底部面板滑入，展示键帽模板网格
    And 顶部提示作用域为「当前段落」

  Scenario: REQ-003 键帽执行模板 (Happy Path)
    Given 面板已打开且作用域已解析
    When 用户按下数字键「2」或点击「逻辑」键帽
    Then 以该作用域发起逻辑链伴读流

  Scenario: REQ-004 关闭面板 (Happy Path)
    Given 面板已打开
    When 用户按下 Esc 或点击面板外区域
    Then 面板收起且正文保持不变
```
