# ADR 002: 跨语言 FFI 通信与统一信封契约协议决策

**状态**：ACCEPTED  
**决策日期**：2026-10-10  
**决策者**：项目架构委员会  

---

## 1. 决策背景 (Context)

表现层 Flutter (Dart) 需要高效、低延迟、无网络端口依赖地调用 Rust 计算引擎能力。通信层必须保证全平台沙盒环境下的安全执行，杜绝防火墙报警与端口冲突。

## 2. 决策选项 (Options Considered)

1. **Option 1: C-FFI 动态链接 + 统一 JSON Envelope 信封**：通过标准 C ABI 传递 UTF-8 JSON 字符串，统一请求与响应协议。
2. **Option 2: 本地 TCP/HTTP REST 守护进程**：绑定 127.0.0.1 端口。
3. **Option 3: 原生 Platform Channel (MethodChannel)**：需要每端针对 Java/Objective-C/C++ 单独写转接层。

## 3. 决策结果 (Decision Outcome)

**选择 Option 1**：
- 导出单一极简 C-ABI 入口：`char* ai_reader_invoke(const char* action, const char* payload)` 与内存释放函数 `void ai_reader_free_string(char* ptr)`；
- 统一信封格式：
  ```json
  {
    "code": 0,
    "message": "OK",
    "data": { ... },
    "metrics": { "duration_ms": 12.5 }
  }
  ```
- 桌面端直接加载动态库（`.so`/`.dll`/`.dylib`），移动端静态链接嵌入。
