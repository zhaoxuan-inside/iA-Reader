# 子特性需求与功能规格说明书 (Feature PRD)：多端构建与本地数据治理

- **特性ID (Feature ID)**：`FEAT-011`
- **特性名称**：多端构建与本地数据治理
- **所属模块**：`platform`
- **优先级**：P0
- **状态**：frozen
- **宏观品味宪章继承**：`Inherits: /DESIGN.md`
- **上级总览索引**：`_02_feature_spec/_01_human_prd/overview_prd.md`
- **关联界面原型**：`_02_feature_spec/_04_prototype_wireframe/platform_distribution_prototype.md`
- **面向 VibeCoding 契约**：`_02_feature_spec/_02_vibe_spec/platform_distribution_vibe_spec.md`

> [!NOTE]
> **微观施工图定位**：定义 MVP 主交付平台（Linux/Windows/Android）与本地数据治理（集中存储、迁移、打包）。

---

## 1. 特性洞察与核心价值界定 (Framing & Discovery)

- **现状与摩擦 (Status Quo)**：运行期产物（数据/配置/日志/书籍）散落在工作目录或多处，升级或换目录后数据易丢；多端各自为政，行为不一致。
- **用户雇佣任务 (JTBD)**：`When` 我在不同设备上使用，`I want to` 让所有数据集中在一个可预期的本地目录并可迁移，`so I can` 放心升级与备份，多端行为一致。
- **惊喜时刻 (Aha Moment)**：首次启动自动把旧位置数据迁入 `~/.ai-reader`，用户无感知、零丢失。
- **冷启动体验 (FTUE)**：首次启动自动创建 `data/config/logs/books` 四个目录并可用；无任何手工配置。

---

## 2. 交互形态比选与取舍 (Approaches & Trade-offs)

| 评估维度 | 方案 A（推荐采纳） | 方案 B（备选弃用） | 取舍理由 (Trade-off Rationale) |
|---|---|---|---|
| **数据位置** | 统一 `~/.ai-reader/{data,config,logs,books}` + 可配置重定位 | 应用目录旁散落 | 集中可预期、便于备份；避免混入工程目录 |
| **迁移** | 首次启动检测旧位置 → 自动迁移 | 用户手工搬移 | 零门槛、防丢数据 |
| **多端** | 同一 Rust 引擎 + 同一 FFI 契约，三端复用 | 各端独立实现 | 保证行为一致、维护成本低 |
| **打包产物** | 统一收敛到 `output/<client>/` | 散落各处 | 工程整洁、可追溯 |

---

## 3. 详细字段与业务规则约束矩阵 (Specifications & Constraints)

| 字段/参数名 | 披露层级 | 类型 | 必填 | 校验规则与边界极端值 | 默认值与微文案提示 |
|---|---|---|---|---|---|
| `home_dir` | 内部 | 字符串 | 是 | 默认 `~/.ai-reader`；可配置覆盖 | ~/.ai-reader |
| `sub_dirs` | 内部 | 列表 | 是 | `data`/`config`/`logs`/`books` 原子创建 | — |
| `migrated` | 内部 | 布尔 | 是 | 幂等，迁移完成即置 true | false |
| `client_target` | 构建 | 枚举 | 是 | `linux`/`windows`/`android` | 当前平台 |

### 业务分支规则矩阵
1. **分支 1（首次启动）**：目录不存在 → 原子创建四目录 → 初始化配置与数据库。
2. **分支 2（检测到旧数据）**：迁移旧位置 → 成功后清理或留观（幂等，可重入）。
3. **分支 3（自定义位置）**：用户配置覆盖路径 → 校验可写 → 生效并记忆。
4. **分支 4（权限不足）**：目标不可写 → 明确报错 + 建议（换路径或修权限），不静默失败。
5. **分支 5（多端打包）**：按 `output/<client>/` 收敛产物；Android 需配对符号表。

---

## 4. 需求原子分解与行为驱动验收标准 (Requirements & Functional DoD)

### 4.1 核心需求原子分解清单 (Atomic Requirements Matrix)
| 需求编号 | 需求名称与规则简述 | 关联字段/动作 | 验收物理证据 | 优先级 |
|---|---|---|---|---|
| `REQ-001` | 运行期产物集中 `~/.ai-reader` 四目录 | 首次启动 | 四目录存在，数据库与配置就位 | P0 |
| `REQ-002` | 旧位置数据自动迁移（幂等） | 检测到旧数据 | 数据迁入新位置，无丢失，可重入 | P0 |
| `REQ-003` | 数据目录可配置重定位 | 修改配置 | 新路径生效并创建，旧数据保留 | P1 |
| `REQ-004` | 三端统一 FFI 契约一致 | 跨端调用 | 同一 action 在三端返回结构一致 | P0 |
| `REQ-005` | 打包产物收敛 `output/<client>/` | 构建 | 产物仅在对应子目录，含版本号 | P0 |
| `REQ-006` | 权限不足给出可行动报错 | 不可写路径 | 明确原因 + 修复建议，不静默失败 | P1 |

### 4.2 行为驱动产品验收场景 (Gherkin Scenarios)

```gherkin
Feature: 多端构建与本地数据治理

  Scenario: REQ-001 首次启动集中目录 (Happy Path)
    Given 用户首次启动且 ~/.ai-reader 不存在
    When 应用初始化
    Then 原子创建 data/config/logs/books 四个子目录
    And 数据库与默认配置就位可读写

  Scenario: REQ-002 旧位置自动迁移 (Happy Path)
    Given 检测到旧位置存在历史数据
    When 应用初始化
    Then 历史数据被迁入 ~/.ai-reader 且无丢失
    And 再次启动不重复迁移（幂等）

  Scenario: REQ-006 权限不足可行动报错 (Error Recovery)
    Given 目标数据目录不可写
    When 应用尝试初始化
    Then 展示明确原因与修复建议（更换目录或调整权限）
    And 不静默失败、不产生半成品数据

  Scenario: REQ-004 三端 FFI 契约一致 (Contract)
    Given 同一 action 与 payload
    When 在 Linux / Windows / Android 分别调用
    Then 返回信封结构（code/message/data/metrics）完全一致
```
