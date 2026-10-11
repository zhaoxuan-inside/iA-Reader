# 任务详细设计与执行记录：task_10_theme_render_bugfix

- **任务名称**：用户报告双缺陷修复——顶栏悬停抖动 / 白天模式文字不可见
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：agent
- **开始时间**：`2026-10-11T07:10:00Z`
- **最后更新**：`2026-10-11T08:00:00Z`

---

## 1. 任务背景与目标

用户实测 v0.0.5（task_09 构建安装态）报告：
1. 鼠标放在导航栏，一直在抖动；
2. 白天模式字体未变成黑色导致看不到文字。

排查确认为**三个独立根因叠加**（缺陷 2 实为两个缺陷复合），全部修复并实机复拍验证。

---

## 2. 根因定位（证据链）

### 根因 A：顶栏悬停抖动（缺陷 1）
`main.dart` 中顶栏自动隐退的唤出条件为纯位置接近（`e.position.dy < 48`）。
阅读时指针停在顶栏附近：滚轮下滚→隐退（下滚 44px 视口变化）→指针微动→唤出→
内容跳变，与「下滚隐退」互相触发形成持续抖动循环。

### 根因 B：Impeller(OpenGLES) 主题切换后陈旧上色（缺陷 2a）
Flutter 3.47.7 Linux GL 默认启用 Impeller。本机驱动栈上暗色启动后切亮色：
顶栏容器/标题/副标题/正文沿用暗色主题颜色绘制（浅字浅底不可见）。
- widget test golden 渲染正常（软渲染管线）→ 排除主题代码错误；
- release 实拍（layer.toImage）复现混合陈旧帧；
- 连续 setState 重建与 MaterialApp 整树重建（Key 变更）均无法恢复
  → 引擎全局缓存（字形图集/图层快照），非 Flutter 层缓存。

### 根因 C：doc.get FFI 契约不匹配——正文从未渲染（缺陷 2b）
真实引擎 doc.get 返回 `sections[].content`（整章 markdown），无 `paragraphs` 字段；
前端 `_loadDocumentData` 读取 `sec['paragraphs']`（bridge mock 契约）恒为空。
**正文段落在暗色模式下也从未渲染**，阅读区仅标题+副标题；切亮色后连标题都不可见，
用户感知为「白天模式看不到文字」。顶层 `title` 字段同样缺失（一直显示 mock 默认书名）。

---

## 3. 修复方案
1. **main.dart**：顶栏唤出加方向门控——仅指针明确向上移动（`delta.dy < -1.0`）且
   接近顶缘时唤出；指针微动不再唤出。上滚唤出/下滚隐退行为不变。
2. **linux/runner/my_application.cc**：`fl_dart_project_set_enable_impeller(project, FALSE)`
   固定走 Skia 后端（release 安全的公开 API；FLUTTER_ENGINE_SWITCHES 环境变量通道
   在 release 构建被引擎裁剪，不可用）。
3. **backend/src/ffi.rs**：doc.get 组装 `sections[].paragraphs[]`（sentence_node 切片
   优先，缺失时按空行切分 content 兜底、跳过 markdown 标题行），顶层补 `title`。
   纯增量，保留原 section 字段与 meta。
4. **reader_engine_bridge.dart**：dlopen 不搜索 CWD，裸名候选 `libreader_core.so`
   存在 existsSync 通过但命中 ldconfig 其它库的隐患——改为 `./libreader_core.so`；
   补 `../backend/target/release/...` 候选（CWD=frontend 的开发态可命中开发引擎）。

## 4. 验证
- `cargo test` 26/26；`flutter analyze` 0 error（20 条历史 info 级 lint）；
- `flutter test` 11/11（含新增回归测试 test/header_reveal_jitter_test.dart：
  微动不唤出/明确上移唤出/下滚隐退/上滚唤出；与 goldens 白天模式渲染抓帧）；
- release 实拍复现→修复→复拍：白天模式下顶栏浅色、标题深色、正文段落完整可读，
  顶栏标题显示真实书名 welcome_guide；
- deb 重打包：output/linux/ai-reader_0.0.5_amd64.deb（含新引擎与新前端）。

## 5. 遗留与备注
- Impeller 在 Linux GL 的陈旧上色疑为引擎缺陷（Flutter 3.47.7 / OpenGLESSDF），
  待上游验证后再评估重新启用；
- 悬停唤出阈值 -1.0px/event 为经验值，触控板慢速上推可能需要多次累积位移；
- `_03_verify_log` 空目录，本次验证记录以本文件为准。
