# 任务计划账本：task_09_ia_design_convergence

- **task_id**：`task_09_ia_design_convergence`
- **标题**：UI 设计语言收敛 iA Writer（打包 iA 开源字体 / 去 emoji / Material 残留清扫 / 规范对齐）
- **change_size**：`M`（触达 UI 多文件与资产管线，无业务逻辑变更）
- **work_mode**：`IMPLEMENT`
- **当前阶段**：`6 - 门禁全绿，COMPLETED`
- **断点**：`S8` — S8
- **更新时间**：`2026-10-11T06:18:55Z`

## 设计决策

见 `hs_dev_docs/_00_project/_05_decision_record/ADR_006_ia_design_convergence.md`：
① 打包 iA 官方开源字体 iA Writer Duo/Mono（OFL 1.1，Static 构建，CJK 回退系统思源宋体）；
② 规范-代码对齐（控件 sans / 正文 Duo / 元数据 mono / 正文 -0.2px 字距）；
③ 界面零 emoji（胶囊/SnackBar/mock 文案改纯文字标签，原则写入 DESIGN.md §1）；
④ Material 残留清扫（胶囊去投影、导入/保存按钮去填充、输入框底线式）。

## 步骤

| step_id | 描述 | 状态 | 备注 |
|---------|------|------|------|
| S0 | 任务创建与 plan_log | done | task_manager + IN_PROGRESS |
| S1 | ADR_006 + checkpoint | done | `_00_project/_05_decision_record/ADR_006_ia_design_convergence.md` |
| S2 | 字体下载入资产（Duo×3 + Mono×2 + LICENSE/README） | done | github.com/iaolo/iA-Fonts, OFL |
| S3 | pubspec 注册 + 主题对齐 | done | analyze 0 error |
| S4 | 去 emoji（枚举/SnackBar/mock/DESIGN.md 示意图） | done | 全仓 emoji 清零 |
| S5 | Material 清扫（胶囊去阴影/文字按钮/底线输入框） | done | InkWell→GestureDetector 去涟漪 |
| S6 | 测试断言更新 + 门禁 + DESIGN.md 对齐 | done | flutter test 8/8；release 构建字体入包验证 |
| S7 | 重打包安装 + 启动冒烟 | done | 安装态字体文件确认；GUI 启动正常 |
| S8 | change_log 归档 + 本地 Commit | doing | 默认本地 commit，不 push |

## DoD 结果

1. 字体资产随 deb 分发（安装态已验证 5 个 ttf + LICENSE）；✅
2. 全仓界面 emoji 清零、胶囊零投影、按钮纯文字、输入框底线式；✅
3. flutter analyze 0 error、flutter test 8/8；✅
4. DESIGN.md §1/§3/§4.2 与代码一致（零 emoji 原则、字距 -0.01em、字体资产落地说明）。✅
