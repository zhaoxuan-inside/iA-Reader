// backend/src/bin/ai_reader_cli.rs
// AI Reader 无头 CLI：与 GUI 共用同一 Rust 引擎（libreader_core 的 dispatch_invoke）。
// 双引擎时代（Python CLI + Rust GUI）已终结：同一 action 在两种宿主下结构、
// 能力与行为完全一致——CLI 只是 C-ABI 信封之上的薄壳。
//
// 用法：
//   ai_reader_cli parse <file>                      解析文档入库
//   ai_reader_cli books                             书库列表
//   ai_reader_cli keywords <book_id> [top_n]        关键词词云
//   ai_reader_cli graph <book_id> [min_co]          概念共现图谱
//   ai_reader_cli mindmap <book_id>                 知识导图
//   ai_reader_cli ask <book_id> <text> [prompt]     伴读分析（阻塞至终态）
//   ai_reader_cli invoke --action X [--payload JSON] [--pretty]  低层信封直调

use std::io::Write;

const HELP: &str = "AI Reader - Headless Core Computation & Document Parsing Engine CLI

USAGE:
    ai_reader_cli <COMMAND>

COMMANDS:
    parse <file>                          解析 Markdown/TXT 文档入库
    books                                 列出书库
    keywords <book_id> [top_n]            提取关键词词云
    graph <book_id> [min_co_occurrence]   构建概念共现图谱
    mindmap <book_id>                     生成知识导图
    ask <book_id> <text> [prompt]         伴读认知分析（离线时返回启发卡片）
    invoke --action <A> [--payload <JSON>] [--pretty]
                                          低层 ai_reader_invoke 直调
    --help                                显示本帮助

ENV:
    AI_READER_HOME    集中存储根目录（缺省 ~/.ai-reader）
";

/// 与 C-ABI ai_reader_invoke 同构的信封包装：dispatch_invoke 返回 data 本体，
/// CLI 侧补齐 code/message 信封语义（0=成功，非 0=错误）
fn invoke(action: &str, payload: serde_json::Value) -> Result<serde_json::Value, String> {
    let payload_str = serde_json::to_string(&payload).map_err(|e| e.to_string())?;
    match reader_core::dispatch_invoke(action, &payload_str) {
        Ok(data) => Ok(serde_json::json!({
            "code": 0,
            "message": "success",
            "data": data,
        })),
        Err(message) => Ok(serde_json::json!({
            "code": 50001,
            "message": message,
            "data": null,
        })),
    }
}

fn print_envelope(envelope: &serde_json::Value, pretty: bool) {
    let text = if pretty {
        serde_json::to_string_pretty(envelope).unwrap_or_default()
    } else {
        envelope.to_string()
    };
    // 管道下游提前关闭（| head 等）不得 panic：静默忽略写失败
    let mut out = std::io::stdout().lock();
    let _ = writeln!(out, "{text}");
}

fn envelope_ok(envelope: &serde_json::Value) -> bool {
    envelope.get("code").and_then(|c| c.as_i64()) == Some(0)
}

fn main() {
    // stdout 只承载机器可读输出：引擎日志镜像改走 stderr
    reader_core::log::mirror_logs_to_stderr();
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() || args[0] == "--help" || args[0] == "help" {
        print!("{HELP}");
        std::process::exit(0);
    }

    let (code, message) = run(&args);
    if code != 0 {
        eprintln!("[ERROR] {message}");
        std::process::exit(1);
    }
}

fn run(args: &[String]) -> (i32, String) {
    let cmd = args[0].as_str();
    let result: Result<(), String> = (|| {
        match cmd {
            "parse" => {
                let file = args.get(1).ok_or("parse 需要 <file> 参数")?;
                let env = invoke(
                    "book.parse",
                    serde_json::json!({ "file_path": file }),
                )?;
                if !envelope_ok(&env) {
                    return Err(format!(
                        "book.parse 失败: {}",
                        env["message"].as_str().unwrap_or_default()
                    ));
                }
                let id = env["data"]["id"].as_i64().unwrap_or(0);
                let title = env["data"]["title"].as_str().unwrap_or_default();
                println!("[SUCCESS] Document parsed successfully: book_id={id} title={title}");
                print_envelope(&env, true);
                Ok(())
            }
            "books" => {
                let env = invoke("book.list", serde_json::json!({}))?;
                print_envelope(&env, true);
                Ok(())
            }
            "keywords" => {
                let book_id: i64 = args
                    .get(1)
                    .ok_or("keywords 需要 <book_id>")?
                    .parse()
                    .map_err(|_| "book_id 必须是整数")?;
                let top_n: i64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(30);
                let env = invoke(
                    "nlp.keyword_extract",
                    serde_json::json!({ "book_id": book_id, "top_n": top_n }),
                )?;
                print_envelope(&env, true);
                Ok(())
            }
            "graph" => {
                let book_id: i64 = args
                    .get(1)
                    .ok_or("graph 需要 <book_id>")?
                    .parse()
                    .map_err(|_| "book_id 必须是整数")?;
                let min_co: i64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(1);
                let env = invoke(
                    "nlp.build_graph",
                    serde_json::json!({ "book_id": book_id, "min_co_occurrence": min_co }),
                )?;
                print_envelope(&env, true);
                Ok(())
            }
            "mindmap" => {
                let book_id: i64 = args
                    .get(1)
                    .ok_or("mindmap 需要 <book_id>")?
                    .parse()
                    .map_err(|_| "book_id 必须是整数")?;
                let env = invoke("mindmap.generate", serde_json::json!({ "book_id": book_id }))?;
                print_envelope(&env, true);
                Ok(())
            }
            "ask" => {
                let book_id: i64 = args
                    .get(1)
                    .ok_or("ask 需要 <book_id>")?
                    .parse()
                    .map_err(|_| "book_id 必须是整数")?;
                let text = args.get(2).ok_or("ask 需要 <text>（划选文本）")?;
                let prompt = args.get(3).cloned().unwrap_or_default();
                let env = invoke(
                    "ai.companion_ask",
                    serde_json::json!({
                        "book_id": book_id,
                        "template_type": "general",
                        "selected_text": text,
                        "prompt": prompt,
                    }),
                )?;
                if let Some(resp) = env["data"]["response"].as_str() {
                    let mut out = std::io::stdout().lock();
                    let _ = writeln!(out, "{resp}");
                } else {
                    print_envelope(&env, true);
                }
                Ok(())
            }
            "invoke" => {
                let mut action = String::new();
                let mut payload = serde_json::json!({});
                let mut pretty = false;
                let mut i = 1;
                while i < args.len() {
                    match args[i].as_str() {
                        "--action" => {
                            action = args.get(i + 1).cloned().ok_or("--action 需要值")?;
                            i += 2;
                        }
                        "--payload" => {
                            let raw = args.get(i + 1).ok_or("--payload 需要值")?;
                            payload = serde_json::from_str(raw)
                                .map_err(|e| format!("payload JSON 无效: {e}"))?;
                            i += 2;
                        }
                        "--pretty" => {
                            pretty = true;
                            i += 1;
                        }
                        other => return Err(format!("未知参数: {other}")),
                    }
                }
                if action.is_empty() {
                    return Err("invoke 需要 --action".to_string());
                }
                let env = invoke(&action, payload)?;
                print_envelope(&env, pretty);
                if !envelope_ok(&env) {
                    std::process::exit(1);
                }
                Ok(())
            }
            other => Err(format!(
                "未知命令: {other}（可用: parse/books/keywords/graph/mindmap/ask/invoke）"
            )),
        }
    })();

    let _ = std::io::stdout().flush();
    match result {
        Ok(()) => (0, String::new()),
        Err(e) => (1, e),
    }
}
