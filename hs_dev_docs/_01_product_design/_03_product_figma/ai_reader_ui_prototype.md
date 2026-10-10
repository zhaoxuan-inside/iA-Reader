# 产品原型：AI Reader 极简沉浸式多端阅读工作台

- **功能**：AI Reader 极简沉浸式多端阅读工作台 (Flutter Multi-platform UI)
- **来源**：Agent 基于 iA Writer 设计哲学与用户对齐结论生成
- **介质**：Mermaid 交互线框原型 + 状态机流转图
- **关联 PRD**：`_02_product_design/ai_reader_full_feature_prd.md`
- **状态**：APPROVED (Frozen - Fully Aligned with iA Writer & 5-Platform Architecture)

---

## 1. 范围与非目标 (Scope & Non-Goals)

### 1.1 覆盖范围
1. **多端自适应布局**：支持 Windows、Linux、macOS、iOS、Android 5 端响应式适配；
2. **核心沉浸阅读区**：定宽黄金版心（680px~720px），支持长文平滑滚动、目录锚点跳转与段落精准对齐；
3. **段落级柔和失焦 (Focus Mode)**：聚焦段落保持 100% 清晰度，上下文段落平滑淡化至 65%，按 Esc/双击恢复；
4. **划词快速伴读胶囊**：原地轻量悬浮，直通 4 大认知模板（⚡️通俗、🔗逻辑、🧐批判、📖术语）与高亮标注；
5. **抽屉式认知伴读流**：桌面端右侧隐式侧栏/移动端 Bottom Sheet，流式展示思考链，支持**卡片内原位追问**并一键沉淀为 SQLite 边注；
6. **极简目录与思维导图**：轻量左侧栏，无感折叠，支持一键预览基于 AST 与 PMI 拓扑生成的知识全景树。

### 1.2 非目标
- 不做杂乱的社交分享、点赞、书评社区功能；
- 不在阅读主界面堆砌常驻编辑按钮、换行标尺与复杂格式刷；
- 移动端不做与桌面端完全一致的双侧常驻展开（移动端强制采用轻量抽屉与底部滑层）。

---

## 2. 主路径（核心阅读与伴读链路）

```mermaid
flowchart LR
  Start["1. 打开书籍/文档"] --> Reading["2. 沉浸阅读 (UI自动隐退)"]
  Reading --> SelectText["3. 划词/选中文本\n(触发段落失焦聚焦)"]
  SelectText --> FloatingPill["4. 悬浮胶囊直选模板\n(⚡️/🔗/🧐/📖)"]
  FloatingPill --> StreamAI["5. 伴读抽屉展开\n流式认知洞察"]
  StreamAI --> FollowUp["6. 卡片内原位追问 (可选)"]
  FollowUp --> PinNote["7. 一键存为持久化边注"]
  PinNote --> ReturnRead["8. 无缝返回阅读心流"]
```

---

## 3. 屏布局线框（Mermaid Wireframes）

### 3.1 桌面端主工作台 (Desktop: macOS / Windows / Linux)

```mermaid
flowchart TB
  subgraph DesktopWorkspace["桌面端主工作台 (iA Writer 排版与失焦聚焦模式)"]
    direction TB
    
    subgraph TopBar["极简自动隐退顶栏 (高度 44px - 悬停显现)"]
      BtnNav["[ ≡ 目录/导图 ]"]
      DocTitle["《高性能分布式架构设计》 · 第 3 章 并发控制 (居中淡灰)"]
      BtnAI["[ 伴读抽屉 ≡ ]"]
      BtnNav --- DocTitle --- BtnAI
    end

    subgraph MainContentArea["主内容工作区 (无缝横向分布)"]
      direction LR

      subgraph LeftSidebar["左侧可折叠抽屉 (260px)"]
        TabDir["[ 章节 AST 目录 ]"]
        TabMindmap["[ 知识导图预览 ]"]
        DirTree["- 1. 概述\n- 2. 存储引擎\n- 3. 并发控制 (当前)\n  - 3.1 MVCC\n  - 3.2 WAL 协议"]
        TabDir --- TabMindmap --- DirTree
      end

      subgraph ReaderCanvas["中央沉浸阅读流 (版心定宽 700px 居中)"]
        Para1["[65% 不透明度淡灰] 在现代分布式数据库设计中，写入日志（WAL）是保证原子性与持久性的关键机制……"]
        
        subgraph SelectedBlock["【100% 对比度】划词选中高亮区 (当前焦点段落)"]
          direction TB
          PillMenu["[ ⚡️通俗 | 🔗逻辑 | 🧐批判 | 📖术语 | 🖍高亮 ] (悬浮药丸)"]
          FocusSentence["【SQLite 在 WAL 模式下，读取者绝不阻塞写入者，写入者也绝不阻塞读取者。】"]
          PillMenu --> FocusSentence
        end

        Para2["[65% 不透明度淡灰] 这极大地提升了系统的整体并发读写吞吐量。然而在检查点执行期间，仍需协调文件刷新……"]

        Para1 --> SelectedBlock --> Para2
      end

      subgraph RightCompanion["右侧认知伴读抽屉 (380px)"]
        CompHeader["[ 认知伴读 · 逻辑链推理 ]    [💾存边注] [✕收起]"]
        CompCard["1. 前置条件：WAL 模式通过分离主数据库与日志文件实现多版本共存。\n2. 核心因果：读操作访问只读快照，写操作追加日志，因此锁竞争完全消除。\n3. 边界隐患：若检查点落后，WAL 文件无限增长会导致读性能衰减。"]
        CompInput["[ 追问本段细节 (Enter发送)... ]"]
        CompActions["[ 💾 保存为段落边注 ]  [ 📋 复制结论 ]"]
        CompHeader --> CompCard --> CompInput --> CompActions
      end

      LeftSidebar --- ReaderCanvas --- RightCompanion
    end

    TopBar --> MainContentArea
  end
```

---

### 3.2 移动端竖屏布局 (Mobile: iOS / Android)

```mermaid
flowchart TB
  subgraph MobileLayout["移动端全屏阅读与自适应 Bottom Sheet"]
    direction TB
    
    subgraph MobileHeader["移动端极简顶栏"]
      MMenu["[ ≡ 目录 ]"]
      MTitle["第 3 章 并发控制"]
      MProgress["68%"]
      MMenu --- MTitle --- MProgress
    end

    subgraph MobileReader["单栏全屏阅读版心"]
      MPara1["在现代分布式数据库设计中，写入日志（WAL）是保证原子性与持久性的关键机制……"]
      MPill["[ ⚡️通俗  🔗逻辑  🧐批判  📖术语 ] (划词浮层)"]
      MPara2["【SQLite 在 WAL 模式下，读取者绝不阻塞写入者……】 (划词选区)"]
      MPara3["这极大地提升了系统的整体并发吞吐量……"]
      MPara1 --> MPill --> MPara2 --> MPara3
    end

    subgraph MobileBottomSheet["半屏可拖拽伴读抽屉 (向上滑动展开/轻扫关闭)"]
      SheetDragHandle["── (拖拽柄) ──"]
      SheetTpl["⚡️ 通俗解读"]
      SheetContent["简单来说，就像食堂打饭：以前是打菜师傅和盛饭师傅抢同一个勺子，现在分成两条独立传送带，谁也不用等谁。"]
      SheetAction["[ 存为边注 ]  [ 收起 ]"]
      SheetDragHandle --> SheetTpl --> SheetContent --> SheetAction
    end

    MobileHeader --> MobileReader --> MobileBottomSheet
  end
```

---

## 4. 与 PRD / DoD 映射关系 (Traceability Matrix)

| 原型组件与交互 | 关联 PRD 模块 | 核心能力与 DoD 验收标准 |
|---|---|---|
| **ReaderCanvas** (中央阅读版心) | F-01, F-02 | 统一呈现 AST 解析出的正文、章节与段落，准确高亮锚点与字符偏移量。 |
| **Floating Action Pill** (划词药丸) | F-04 | 选词/选句后毫秒级就绪，直达 4 套认知模板上下文装配。 |
| **RightCompanion** (伴读抽屉) | F-04 | 承载流式输出（TTFT < 800ms），断网时毫秒级呈现离线确定性启发卡。 |
| **TabMindmap** (导图与拓扑抽屉) | F-05, F-06 | 结合本地三级 NLP（TF-IDF + PMI 拓扑）与目录 AST 呈现层级导图树。 |
| **CompActions -> 存为边注** | F-03, F-07 | 增量原子写入本地 SQLite，将 AI 洞察持久化绑定在段落锚点。 |
| **5-Platform Responsive** | F-08 | 基于 Flutter 引擎，全平台统一六元组 FFI 桥接接入。 |
