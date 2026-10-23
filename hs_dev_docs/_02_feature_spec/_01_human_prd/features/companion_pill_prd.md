# 子特性需求与功能规格说明书 (Feature PRD)：划词伴读胶囊

- **特性ID (Feature ID)**：`FEAT-004`
- **特性名称**：划词伴读胶囊
- **所属模块**：`companion`
- **优先级**：P0
- **状态**：frozen
- **宏观品味宪章继承**：`Inherits: /DESIGN.md`
- **上级总览索引**：`_02_feature_spec/_01_human_prd/overview_prd.md`
- **关联界面原型**：`_02_feature_spec/_04_prototype_wireframe/companion_pill_prototype.md`
- **面向 VibeCoding 契约**：`_02_feature_spec/_02_vibe_spec/companion_pill_vibe_spec.md`

> [!NOTE]
> **微观施工图定位**：本特性是 Aha Moment 的直达入口——把"划选→唤起 AI"压缩到 <50ms 与 1 次点击。

---

## 1. 特性洞察与核心价值界定 (Framing & Discovery)

- **现状与摩擦 (Status Quo)**：遇到难懂段落时，用户要"选中→复制→切到浏览器/对话框→粘贴→提问"，上下文切换成本极高，心流被彻底打断。
- **用户雇佣任务 (JTBD)**：`When` 我在阅读中碰到读不懂的一句，`I want to` 就地唤起一个轻量操作条并一键选择解读角度，`so I can` 不离开正文就获得解释。
- **惊喜时刻 (Aha Moment)**：松开鼠标的一瞬，一个纯色药丸在选区下方 10px 冒出并跟随，5 个 mono 文字标签（通俗/逻辑/批判/术语/高亮）清晰可点——**零跳转**。
- **冷启动体验 (FTUE)**：选中示例文章的任一句即出现胶囊；未配置 LLM 时点击模板会引导进入设置，而非报错死胡同。

---

## 2. 交互形态比选与取舍 (Approaches & Trade-offs)

| 评估维度 | 方案 A（推荐采纳） | 方案 B（备选弃用） | 取舍理由 (Trade-off Rationale) |
|---|---|---|---|
| **唤起形态** | 锚定选区末尾/下方 10px 的浮动药丸，随选区移动并夹紧窗口 | 屏幕角落的固定悬浮按钮 | 就近锚定符合费茨定律，视线与手指移动距离最短 |
| **收起机制** | 点击胶囊外任意区域（含正文）即收起（TapRegion） | 仅 Esc 收起 | 点击外部收起符合直觉，零学习成本；Esc 作为补充 |
| **标签呈现** | mono 文字标签 `[通俗][逻辑][批判][术语][高亮]` | emoji 图标 | 零 emoji 是 `/DESIGN.md` 硬红线；文字标签更克制、无歧义 |

---

## 3. 详细字段与业务规则约束矩阵 (Specifications & Constraints)

| 字段/参数名 | 披露层级 | 类型 | 必填 | 校验规则与边界极端值 | 默认值与微文案提示 |
|---|---|---|---|---|---|
| `selection_text` | 内部 | 字符串 | 是 | 1–2000 字符；超长截断用于模板上下文 | — |
| `selection_rect` | 内部 | 矩形 | 是 | 选区框；失效时回退锚定段落右上角 | — |
| `template` | 首屏可见 | 枚举 | 是 | `general`/`logic`/`critical`/`term`/`highlight` | 无（用户选择） |
| `pill_visible` | 内部 | 布尔 | 是 | true/false；外部点击即 false | false |
| `pill_offset` | 内部 | 整数 | 是 | 10px（选区下方） | 10px |

### 业务分支规则矩阵
1. **分支 1（常规划选）**：mouseup 且选区非空 → 计算锚点 → 药丸淡入（< 50ms）并夹紧可视范围。
2. **分支 2（选区贴近窗口底边）**：药丸改锚定选区**上方** 10px，避免出界。
3. **分支 3（点击胶囊外）**：收起药丸并同步收起选区。
4. **分支 4（点击"高亮"）**：不发 LLM 请求，直接进入高亮标注流（FEAT-007）。
5. **分支 5（未配置 LLM）**：点击认知模板 → 打开设置引导（FEAT-006），保留选区上下文不丢失。

---

## 4. 需求原子分解与行为驱动验收标准 (Requirements & Functional DoD)

### 4.1 核心需求原子分解清单 (Atomic Requirements Matrix)
| 需求编号 | 需求名称与规则简述 | 关联字段/动作 | 验收物理证据 | 优先级 |
|---|---|---|---|---|
| `REQ-001` | 划选文本后 50ms 内浮出药丸并跟随 | 鼠标划选 | 药丸出现在选区下方 10px，跟随选区且夹紧窗口 | P0 |
| `REQ-002` | 5 个 mono 文字标签可达 4 认知模板 + 高亮 | 点击标签 | 触发对应伴读/高亮，无 emoji | P0 |
| `REQ-003` | 点击胶囊外任意区域收起 | 正文/空白点击 | 药丸与选区同步收起 | P0 |
| `REQ-004` | 越界自适应（上下翻转/夹紧） | 选区贴近边缘 | 药丸始终完整可见，不溢出窗口 | P1 |
| `REQ-005` | 未配置 LLM 时引导而非报错 | 点击模板（未配置） | 打开设置引导，保留选区 | P0 |

### 4.2 行为驱动产品验收场景 (Gherkin Scenarios)

```gherkin
Feature: 划词伴读胶囊

  Scenario: REQ-001 划选后即时浮出胶囊 (Happy Path)
    Given 用户正在阅读正文
    When 用户用鼠标划选一个句子并松开
    Then 50ms 内在选区下方 10px 出现纯色药丸
    And 药丸包含 [通俗][逻辑][批判][术语][高亮] 五个 mono 文字标签且无 emoji

  Scenario: REQ-005 未配置 LLM 时引导设置 (Validation)
    Given 用户尚未配置 LLM 连接
    When 用户划词并点击「通俗」标签
    Then 系统打开 LLM 设置引导而非报错
    And 用户取消后可继续阅读且原选区不丢失

  Scenario: REQ-003 点击外部收起 (Happy Path)
    Given 药丸可见
    When 用户点击正文或胶囊外的任意区域
    Then 药丸与选区同时收起

  Scenario: REQ-004 越界自适应 (Edge)
    Given 用户划选靠近窗口底部的文本
    When 药丸需要展示
    Then 药丸翻转到选区上方 10px 并保持完整可见
```
