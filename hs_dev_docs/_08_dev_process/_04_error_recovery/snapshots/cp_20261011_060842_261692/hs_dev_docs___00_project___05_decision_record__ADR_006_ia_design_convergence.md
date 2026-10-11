# ADR 006: UI 设计语言收敛 iA Writer（字体资产 / 去 emoji / Material 残留清扫）

**状态**：ACCEPTED
**决策日期**：2026-10-11
**关联任务**：`task_09_ia_design_convergence`

---

## 1. 决策背景 (Context)

设计语言对标评估结论：骨架（色板/版心/Focus Mode/隐退）高度还原 iA Writer，
但三处偏离：① 字体仅声明回退链未打包资产，iA 的排版身份在运行时不成立；
② 10 处以 emoji 充当功能图标（划词胶囊/SnackBar/mock 文案）；③ Material 控件质感残留
（填充按钮/胶囊投影/描边输入框）。另有 DESIGN.md 两处规范-代码矛盾（控件字体族、正文字距）。

## 2. 决策结果 (Decision Outcome)

1. **字体资产打包**：引入 iA 官方开源字体（github.com/iaolo/iA-Fonts，SIL OFL 1.1，可合法再分发）：
   - `iA Writer Duo`（Regular/Italic/Bold）→ 正文阅读字体（Latin 覆盖）；
   - `iA Writer Mono`（Regular/Bold）→ 元数据/路径等微文案。
   CJK 字符经回退链落 Source Han Serif / Noto Serif CJK（CJK 字体体积 30MB+ 不打包，声明回退）。
2. **规范-代码对齐（以 DESIGN.md 为准）**：
   - 控件与界面 chrome → 无衬线（Inter → PingFang SC → 系统无衬线回退）；
     正文（bodyLarge）显式 `iA Writer Duo` + serif 回退链；
   - 元数据（labelSmall）→ `iA Writer Mono`；
   - 正文字距改 `-0.2`（≈ -0.01em，符合规范）。
3. **去 emoji**：`CognitiveTemplateType` 标签改纯文字（通俗/逻辑/批判/术语/高亮）；
   SnackBar、bridge mock 伴读文案同步去 emoji（界面语言零 emoji 原则写入 DESIGN.md）。
4. **Material 残留清扫**：
   - 划词胶囊去投影，仅保留发丝线边框；选中项以强调蓝表达；
   - 「导入文档」与设置对话框「保存」改纯文字按钮（强调蓝文字、无填充）；
   - 设置对话框输入框改底线式（去 OutlineInputBorder 描边框）。

## 3. 后续影响 (Consequences)

### 正向影响
- 排版身份在任意机器一致成立（不依赖用户是否安装字体）；
- 界面语言与 iA Writer 的「文字即界面」原则对齐，视觉噪音显著下降；
- DESIGN.md 与代码不再互相矛盾，验收有据可依。

### 风险与应对
- OFL 协议要求保留版权声明 → 字体目录附 LICENSE 与来源 README；
- CJK 用户若系统无思源宋体 → 回退到系统默认衬线（与改动前一致，无回退风险）；
- widget 测试断言含 emoji 标签 → 同步更新为纯文字断言。
