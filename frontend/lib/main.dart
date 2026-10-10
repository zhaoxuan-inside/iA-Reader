// frontend/lib/main.dart
import 'package:flutter/material.dart';
import 'features/reader/reader_controller.dart';

void main() {
  runApp(const AiReaderApp());
}

class AiReaderApp extends StatelessWidget {
  const AiReaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Reader',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFFBFBF9), // Editorial Stone 背景
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2C3E50),
          surface: const Color(0xFFFBFBF9),
        ),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(
            fontSize: 18.0,
            height: 1.8, // 1.8em 黄金行高
            color: Color(0xFF1E293B),
            fontFamily: 'serif',
          ),
        ),
      ),
      home: const MainReaderWorkbench(),
    );
  }
}

class MainReaderWorkbench extends StatefulWidget {
  const MainReaderWorkbench({super.key});

  @override
  State<MainReaderWorkbench> createState() => _MainReaderWorkbenchState();
}

class _MainReaderWorkbenchState extends State<MainReaderWorkbench> {
  final ReaderController controller = ReaderController();

  @override
  void initState() {
    super.initState();
    controller.loadBook(1, "深度学习导论");
    controller.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024;

    return Scaffold(
      appBar: AppBar(
        title: Text(controller.currentTitle.isEmpty ? 'AI Reader' : controller.currentTitle),
        elevation: 0.5,
        backgroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.hub_outlined),
            tooltip: "概念图谱",
            onPressed: () => controller.toggleGraphView(),
          ),
          IconButton(
            icon: const Icon(Icons.account_tree_outlined),
            tooltip: "思维导图",
            onPressed: () => controller.toggleMindmapView(),
          ),
          IconButton(
            icon: const Icon(Icons.download_outlined),
            tooltip: "导出 Markdown 批注",
            onPressed: () {
              final md = controller.exportAnnotationsMarkdown();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("批注已成功导出")),
              );
            },
          ),
        ],
      ),
      body: isDesktop ? _buildDesktopThreeColumnLayout() : _buildMobileSingleColumnLayout(),
    );
  }

  Widget _buildDesktopThreeColumnLayout() {
    return Row(
      children: [
        // 左栏：导图与目录索引
        Container(
          width: 260,
          color: const Color(0xFFF7F7F5),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                controller.isGraphVisible ? "核心概念网络" : "目录与脉络",
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const Divider(),
              Expanded(
                child: ListView(
                  children: const [
                    ListTile(title: Text("1. Introduction & Background"), dense: true),
                    ListTile(title: Text("2. Mathematical Formulation"), dense: true),
                    ListTile(title: Text("3. Attention Mechanisms"), dense: true),
                  ],
                ),
              ),
            ],
          ),
        ),
        const VerticalDivider(width: 1),
        // 中栏：正文沉浸流式排版
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 48.0, vertical: 24.0),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SelectableText(
                    "人类认知的演进是一场不断打破旧有范式的旅程。在这个信息爆炸的时代，深度阅读与认知伴读成为沉淀知识的核心阶梯。\n\n"
                    "Attention Mechanisms have revolutionized sequence modeling in artificial intelligence. By allowing the network to dynamically weight different input tokens, transformers achieve state-of-the-art results across benchmarks.\n\n"
                    "Residual connections provide gradient highways directly to earlier layers, completely solving the vanishing gradient dilemma in deep networks.",
                    style: Theme.of(context).textTheme.bodyLarge,
                    onSelectionChanged: (selection, cause) {
                      controller.onSelectText("Attention Mechanisms", 1, 0);
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
        const VerticalDivider(width: 1),
        // 右栏：iA Writer 风格边注栏 (基线垂直对齐)
        Container(
          width: 300,
          color: const Color(0xFFFAFAFA),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("iA Writer 边注 & 认知伴读", style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Row(
                children: [
                  _templateButton("通俗", "general"),
                  const SizedBox(width: 6),
                  _templateButton("逻辑", "logic"),
                  const SizedBox(width: 6),
                  _templateButton("辩驳", "critical"),
                  const SizedBox(width: 6),
                  _templateButton("术语", "term"),
                ],
              ),
              const Divider(height: 24),
              if (controller.activeCompanionCard.isNotEmpty)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Text(
                    controller.activeCompanionCard['response'] ?? '',
                    style: const TextStyle(fontSize: 13, height: 1.5),
                  ),
                )
              else
                const Text("在正文中选中文字即可激活 4 大认知伴读模板与边注沉淀。", style: TextStyle(color: Colors.grey, fontSize: 13)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _templateButton(String label, String type) {
    return InkWell(
      onTap: () => controller.invokeAiCompanion(type, "分析该段落"),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFFEDF2F7),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
      ),
    );
  }

  Widget _buildMobileSingleColumnLayout() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: SelectableText(
        "移动自适应阅读：人类认知的演进是一场不断打破旧有范式的旅程。在这个信息爆炸的时代，深度阅读与认知伴读成为沉淀知识的核心阶梯。",
        style: Theme.of(context).textTheme.bodyLarge,
      ),
    );
  }
}
