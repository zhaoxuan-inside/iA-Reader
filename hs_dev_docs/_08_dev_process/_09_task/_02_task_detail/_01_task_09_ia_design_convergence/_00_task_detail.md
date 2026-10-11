# 任务详细设计与执行记录：task_09_ia_design_convergence

- **任务名称**：UI设计语言收敛iA Writer：打包iA开源字体/去emoji/Material残留清扫/规范对齐
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T06:08:16Z`
- **最后更新**：`2026-10-11T06:19:17Z`

---

## 1. 任务背景与目标

对标评估发现三处偏离 iA Writer 设计语言：字体未打包（排版身份运行时不成立）、
10 处 emoji 充当功能图标、Material 控件质感残留；另有 DESIGN.md 两处规范-代码矛盾。
本任务按 ADR_006 收敛：打包 iA 官方开源字体（OFL）、界面零 emoji、清扫 Material 残留、
规范与代码互相对齐。视觉收敛任务，无业务逻辑变更。

---

## 2. 验收标准
1. 字体资产随包分发（release bundle 与安装态均含 5 个 ttf + OFL LICENSE）；
2. 全仓界面 emoji 清零；胶囊零投影；导入/保存按钮纯文字；设置输入框底线式；
3. `flutter analyze` 0 error、`flutter test` 8/8 绿（断言同步纯文字标签）；
4. DESIGN.md §1/§3/§4.2 与实现对齐。

---

## 3. 执行步骤 (Checklist)
- [x] 1. ADR_006 + plan_log（纯视觉收敛，无 DB 变更）
- [x] 2. 字体资产管线（下载→license→pubspec→bundle 验证）
- [x] 3. 主题对齐 + 去 emoji + Material 清扫 + 测试断言更新
- [x] 4. DESIGN.md 规范回写（零 emoji 原则/字距/字体资产）
- [x] 5. 门禁全绿 + deb 重打包安装 + 安装态字体与启动验证

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
frontend/assets/fonts/*                                        # 新增 iAWriterDuoS×3 / MonoS×2 + OFL LICENSE + README
frontend/pubspec.yaml                                          # 字体族注册 + LICENSE 资产
frontend/lib/core/theme/reader_theme.dart                      # 正文 Duo/控件 sans/元数据 mono/负字距
frontend/lib/features/selection_pill/presentation/floating_action_pill.dart  # 去 emoji/去阴影/mono 标签/去涟漪
frontend/lib/features/library/presentation/library_screen.dart # 导入按钮去填充
frontend/lib/features/settings/presentation/settings_dialog.dart # 底线输入框/保存纯文字按钮
frontend/lib/main.dart                                         # SnackBar 去 emoji
frontend/lib/core/ffi/reader_engine_bridge.dart                # mock 伴读文案去 emoji
frontend/test/widget_test.dart                                 # 胶囊标签断言改纯文字
DESIGN.md                                                      # §1 零 emoji 原则/§3 字体资产与字距/§4.2 胶囊规范
```

---

## 5. 验证与门禁记录
- `flutter analyze`：0 error；`flutter test`：8/8 绿
- `flutter build linux --release`：成功，bundle 内确认 5 个字体 ttf
- deb 重打包 + chroot 安装：安装态 /usr/lib/ai-reader/data/flutter_assets/assets/fonts/ 字体与 LICENSE 就位
- GUI 启动冒烟正常；全仓（lib/ + DESIGN.md）emoji 清零
