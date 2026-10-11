# 任务详细设计与执行记录：task_11_frosted_modal_ui

- **任务名称**：UI 交互改造——划词胶囊锚定选区/点外即收、单标题栏、AI 伴读与目录导图毛玻璃弹窗化
- **当前状态**：`COMPLETED`
- **优先级**：P1
- **负责人**：agent
- **开始时间**：`2026-10-11T08:20:00Z`
- **最后更新**：`2026-10-11T09:00:00Z`

---

## 1. 任务背景与目标

用户实测 task_10 修复后的安装态提出 6 点交互与视觉需求：
1. 划词功能按钮应出现在被选内容旁（此前为固定 Offset(260,180)）；
2. 点击其他区域，功能按钮应自动消失；
3. 窗口存在双标题栏（GTK 系统标题栏 + 应用内顶栏）；
4. AI 问答改为弹窗形式，不要侧边栏；
5. 目录和知识导图也改为弹窗形式；
6. 弹窗采用毛玻璃：弹窗外内容高斯模糊、弹窗内内容完全不透明、无明显弹窗边界、边界柔和过渡。

## 2. 方案与实现
1. **胶囊锚定**（main.dart）：段落挂 `GlobalKey`，划词时取 RenderBox 全局矩形；
   经 RenderParagraph `getBoxesForSelection` 取选区末尾矩形（TextBox.toRect），
   胶囊置于其下方 10px，回退锚定段落右上角，并 clamp 进窗口可视区；
   在本文内收起选区时同步收起胶囊。
2. **点外即收**：胶囊包 `TapRegion.onTapOutside`（TapRegion 不参与手势竞技场，
   不影响正文选择手势）。
3. **单标题栏**（linux/runner/my_application.cc + Dart）：`gtk_window_set_decorated(FALSE)`；
   MethodChannel `ai.reader/window` 提供 minimize/toggleMaximize/close/beginDrag；
   Wayland 的 begin_move_drag 需要活跃按键 serial——C 侧记录视图上最近一次左键按下
   （button-press-event），beginDrag 时取用；Flutter 侧 `WindowChannel` + `WindowControls`
   （最小化/最大化/关闭，ValueNotifier 共享最大化状态），阅读页顶栏与书库页头部均为拖拽区
   （GestureDetector.onPanStart，仅 pan 不影响子按钮单击时延——勿用 onDoubleTap，会让
   竞技场内所有单击等待 300ms 双击判定）。
4. **FrostedModal**（core/widgets/frosted_modal.dart）：全屏 BackdropFilter(σ≈14) 高斯模糊 +
   轻度压暗；面板 surface 底色完全不透明；三层同色羽化光晕（blur 40/90/150 + spread）替代
   描边/硬阴影，边界柔和过渡；入场 240ms 淡入+缩放；点击面板外关闭，面板内点击被吞。
5. **形态切换**：CompanionDrawer / TocMindmapDrawer 去定宽与侧边框，作为弹窗面板内容
   居中弹出（440×560 / 360×620）；移出主 Row，阅读区不再被侧边抽屉挤压；移动端半屏
   Sheet 形态保留。

## 3. 验证
- `flutter analyze` 0 error；`flutter test` 14/14
  （新增 test/frosted_modal_pill_test.dart：目录弹窗开/点外关、伴读弹窗开/点外关、
   胶囊锚定选区附近 + 点外消失；划词用长按后拖拽确定性构造非折叠选区）；
- release 实拍（layer.toImage 场景化抓帧）：目录弹窗与伴读弹窗背景模糊、面板不透明、
  羽化边界符合 §4.3；XWayland 下 xwd 抓真实窗口：应用内顶栏为唯一标题栏且右端有窗口控制。

## 4. 遗留与备注
- 窗口拖拽的 Wayland 依赖"按住时的按键 serial"：若拖拽起点不在窗口视图上（如键盘触发）
  则忽略；X11 亦验证通过。
- 双击顶栏最大化未实现（onDoubleTap 会让全部子按钮单击延迟 300ms，放弃）；如需可后续用
  Listener 原始事件自行判双击。
- 弹窗打开时阅读位置不重置；侧边抽屉挤压视口导致的滚动位置跳变随形态切换一并消除。
