// backend/src/llm.rs
// LLM 认知伴读客户端：配置读取（与 Python 引擎同构）+ OpenAI 兼容 chat/completions + 指数退避重试
//
// Seam 约定（见 task_06 任务详情）：
// - `LlmConfig::load_from`  : 配置合并优先级 用户 > 默认文件 > 内建缺省
// - `LlmClient::chat`       : 可替换的传输层（生产 UreqLlmClient / 测试 Mock）
// - `chat_with_retry`       : 指数退避重试编排（sleep 可注入，测试零真实等待）
// - `build_companion_messages`: 4 大认知模板 prompt 组装

use serde::Deserialize;
use serde_json::{json, Value};
use std::path::Path;
use std::time::Duration;

/// 重试次数上限（含首次调用），对齐 PRD §4.1「指数退避重试（最多 3 次）」
pub const MAX_RETRIES: u32 = 3;
/// 退避基础延时（毫秒），第 n 次重试前等待 base * 2^(n-1)
pub const BASE_DELAY_MS: u64 = 300;

fn default_provider() -> String {
    "deepseek".to_string()
}
fn default_endpoint() -> String {
    "https://api.deepseek.com/v1".to_string()
}
fn default_model() -> String {
    "deepseek-chat".to_string()
}
fn default_temperature() -> f64 {
    0.7
}
fn default_max_tokens() -> u32 {
    2048
}

/// LLM 配置，字段与 `backend/reader_engine.py::get_llm_config` 及
/// `~/.config/ai-reader/llm_config.json` 完全同构，两端共享同一份用户配置。
#[derive(Debug, Clone, Deserialize)]
pub struct LlmConfig {
    #[serde(default = "default_provider")]
    pub provider: String,
    #[serde(default = "default_endpoint")]
    pub endpoint: String,
    #[serde(default)]
    pub api_key: String,
    #[serde(default = "default_model")]
    pub model_name: String,
    #[serde(default = "default_temperature")]
    pub temperature: f64,
    #[serde(default = "default_max_tokens")]
    pub max_output_tokens: u32,
    #[serde(default)]
    pub system_prompt: String,
}

impl Default for LlmConfig {
    fn default() -> Self {
        serde_json::from_value(json!({})).expect("LlmConfig defaults must deserialize")
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ChatMessage {
    pub role: &'static str,
    pub content: String,
}

/// 传输层 seam：生产实现走 ureq，测试注入 Mock，业务零网络污染。
/// `Send` 约束：ReaderService 存放于静态 Mutex 中，跨线程共享要求传输层可移动。
pub trait LlmClient: Send {
    fn chat(&self, config: &LlmConfig, messages: &[ChatMessage]) -> Result<String, String>;
}

impl LlmConfig {
    /// 合并顺序：内建缺省 < default_config < user_config（键级覆盖，语义对齐 Python dict.update）。
    pub fn load_from(user_config: Option<&Path>, default_config: Option<&Path>) -> LlmConfig {
        let mut merged = serde_json::Map::new();
        for path in [default_config, user_config].into_iter().flatten() {
            if let Ok(text) = std::fs::read_to_string(path) {
                if let Ok(Value::Object(map)) = serde_json::from_str::<Value>(&text) {
                    for (k, v) in map {
                        merged.insert(k, v);
                    }
                }
            }
        }
        serde_json::from_value(Value::Object(merged)).unwrap_or_default()
    }

    /// 真实配置解析：用户配置 `~/.config/ai-reader/llm_config.json`，
    /// 默认配置 `<workspace>/config/default_llm_config.json`（仅存在于开发/源码环境）。
    pub fn load() -> LlmConfig {
        let user = std::env::var("HOME").ok().map(|h| {
            Path::new(&h).join(".config").join("ai-reader").join("llm_config.json")
        });
        let default_path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("config")
            .join("default_llm_config.json");
        let default = if default_path.exists() { Some(default_path) } else { None };
        Self::load_from(user.as_deref(), default.as_deref())
    }
}

/// 4 大认知模板的系统指令（PRD F-04：通俗解读 / 逻辑链条 / 批判审视 / 术语拆解）。
pub fn template_instruction(template_type: &str) -> &'static str {
    match template_type {
        "logic" => "请以「逻辑链条」模板分析：拆解论点前提、推导过程与核心结论，指出论证是否闭合。",
        "critical" => "请以「批判审视」模板分析：从反向视角审视该论述，指出其隐含假设、边界条件与潜在失效场景。",
        "term" => "请以「术语拆解」模板分析：拆解核心术语的定义、内涵外延、易混淆概念与衍生应用。",
        _ => "请以「通俗解读」模板分析：用生活化类比与直白语言解释这段文本的核心思想，降低理解门槛。",
    }
}

/// 组装伴读消息：system = 全局人设 + 模板指令；user = 划选文本（+ 可选追问）。
pub fn build_companion_messages(
    template_type: &str,
    selected_text: &str,
    prompt: &str,
    system_prompt: &str,
) -> Vec<ChatMessage> {
    let mut system = String::from(system_prompt);
    if !system.is_empty() {
        system.push_str("\n\n");
    }
    system.push_str(template_instruction(template_type));

    let mut user = format!("我划选的文本如下：\n\n{}", selected_text);
    if !prompt.trim().is_empty() {
        user.push_str(&format!("\n\n我的追问：{}", prompt));
    }

    vec![
        ChatMessage { role: "system", content: system },
        ChatMessage { role: "user", content: user },
    ]
}

/// 指数退避重试编排：首次失败后按 base*2^(n-1) ms 退避再试，直至耗尽 max_retries。
/// `sleep` 可注入（生产传 std::thread::sleep，测试记录延时序列），保证测试零真实等待。
pub fn chat_with_retry<S>(
    client: &dyn LlmClient,
    config: &LlmConfig,
    messages: &[ChatMessage],
    max_retries: u32,
    base_delay_ms: u64,
    sleep: S,
) -> Result<String, String>
where
    S: Fn(Duration),
{
    let mut attempt: u32 = 0;
    loop {
        match client.chat(config, messages) {
            Ok(content) => return Ok(content),
            Err(err) => {
                attempt += 1;
                if attempt >= max_retries.max(1) {
                    return Err(err);
                }
                sleep(Duration::from_millis(base_delay_ms << (attempt - 1)));
            }
        }
    }
}

/// 生产传输层：OpenAI 兼容 `POST {endpoint}/chat/completions`（deepseek 等均兼容）。
pub struct UreqLlmClient;

/// 单次请求上限：LLM 深度解析生成耗时不定，60s 覆盖长回复同时避免 FFI 线程无限挂起。
const CHAT_TIMEOUT_SECS: u64 = 60;

impl LlmClient for UreqLlmClient {
    fn chat(&self, config: &LlmConfig, messages: &[ChatMessage]) -> Result<String, String> {
        if config.api_key.trim().is_empty() {
            return Err("LLM api_key 未配置".to_string());
        }
        let url = format!("{}/chat/completions", config.endpoint.trim_end_matches('/'));
        let body = json!({
            "model": config.model_name,
            "messages": messages
                .iter()
                .map(|m| json!({ "role": m.role, "content": m.content }))
                .collect::<Vec<_>>(),
            "temperature": config.temperature,
            "max_tokens": config.max_output_tokens,
        });

        let resp = ureq::post(&url)
            .set("Authorization", &format!("Bearer {}", config.api_key.trim()))
            .timeout(Duration::from_secs(CHAT_TIMEOUT_SECS))
            .send_json(body)
            .map_err(|e| format!("LLM request failed: {}", e))?;

        let value: Value = resp
            .into_json()
            .map_err(|e| format!("LLM response decode failed: {}", e))?;

        value
            .get("choices")
            .and_then(|c| c.get(0))
            .and_then(|c| c.get("message"))
            .and_then(|m| m.get("content"))
            .and_then(|c| c.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| format!("LLM response missing choices[0].message.content: {}", value))
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    /// 可注入的 LLM 假实现：按序返回 results，超出后统一 Err；calls/seen_messages 可共享句柄供外部断言。
    pub struct MockLlmClient {
        results: Vec<Result<String, String>>,
        pub calls: Arc<AtomicUsize>,
        pub seen_messages: Arc<AtomicUsize>,
    }

    impl MockLlmClient {
        pub fn new(results: Vec<Result<String, String>>) -> Self {
            Self {
                results,
                calls: Arc::new(AtomicUsize::new(0)),
                seen_messages: Arc::new(AtomicUsize::new(0)),
            }
        }
    }

    impl LlmClient for MockLlmClient {
        fn chat(&self, _c: &LlmConfig, messages: &[ChatMessage]) -> Result<String, String> {
            self.seen_messages.store(messages.len(), Ordering::SeqCst);
            let i = self.calls.load(Ordering::SeqCst);
            self.calls.store(i + 1, Ordering::SeqCst);
            self.results.get(i).cloned().unwrap_or_else(|| Err("mock exhausted".to_string()))
        }
    }

    fn test_config(api_key: &str) -> LlmConfig {
        serde_json::from_value(json!({
            "endpoint": "https://api.example.com/v1",
            "api_key": api_key,
            "model_name": "test-model"
        }))
        .unwrap()
    }

    fn write_temp_config(name: &str, content: &str) -> std::path::PathBuf {
        let path = std::env::temp_dir().join(format!(
            "ai_reader_llm_test_{}_{}",
            name,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::write(&path, content).unwrap();
        path
    }

    #[test]
    fn config_defaults_when_no_files() {
        let cfg = LlmConfig::load_from(None, None);
        assert_eq!(cfg.provider, "deepseek");
        assert_eq!(cfg.endpoint, "https://api.deepseek.com/v1");
        assert_eq!(cfg.model_name, "deepseek-chat");
        assert_eq!(cfg.temperature, 0.7);
        assert_eq!(cfg.max_output_tokens, 2048);
        assert!(cfg.api_key.is_empty());
    }

    #[test]
    fn config_user_overrides_default_file() {
        let default_path = write_temp_config(
            "default",
            r#"{"endpoint": "https://default.example.com/v1", "model_name": "default-model", "max_output_tokens": 4096}"#,
        );
        let user_path = write_temp_config("user", r#"{"api_key": "sk-user-key"}"#);
        let cfg = LlmConfig::load_from(Some(&user_path), Some(&default_path));
        assert_eq!(cfg.api_key, "sk-user-key");
        assert_eq!(cfg.endpoint, "https://default.example.com/v1");
        assert_eq!(cfg.model_name, "default-model");
        assert_eq!(cfg.max_output_tokens, 4096);
        std::fs::remove_file(default_path).ok();
        std::fs::remove_file(user_path).ok();
    }

    #[test]
    fn retry_returns_first_success_without_sleep() {
        let mock = MockLlmClient::new(vec![Ok("真实回复".to_string())]);
        let cfg = test_config("k");
        let msgs = build_companion_messages("general", "文本", "", "人设");
        let out = chat_with_retry(&mock, &cfg, &msgs, MAX_RETRIES, BASE_DELAY_MS, |_| {
            panic!("首次成功不应退避")
        });
        assert_eq!(out.unwrap(), "真实回复");
        assert_eq!(mock.calls.load(Ordering::SeqCst), 1);
        assert_eq!(mock.seen_messages.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn retry_recovers_with_exponential_backoff() {
        let mock = MockLlmClient::new(vec![
            Err("网络抖动".to_string()),
            Ok("恢复后回复".to_string()),
        ]);
        let recorded: std::sync::Mutex<Vec<u64>> = std::sync::Mutex::new(Vec::new());
        let cfg = test_config("k");
        let msgs = build_companion_messages("logic", "文本", "", "");
        let out = chat_with_retry(&mock, &cfg, &msgs, MAX_RETRIES, BASE_DELAY_MS, |d| {
            recorded.lock().unwrap().push(d.as_millis() as u64);
        });
        assert_eq!(out.unwrap(), "恢复后回复");
        assert_eq!(mock.calls.load(Ordering::SeqCst), 2);
        assert_eq!(recorded.lock().unwrap().as_slice(), &[BASE_DELAY_MS]);
    }

    #[test]
    fn retry_exhausts_and_reports_last_error() {
        let mock = MockLlmClient::new(vec![]);
        let recorded: std::sync::Mutex<Vec<u64>> = std::sync::Mutex::new(Vec::new());
        let cfg = test_config("k");
        let msgs = build_companion_messages("term", "文本", "", "");
        let out = chat_with_retry(&mock, &cfg, &msgs, MAX_RETRIES, BASE_DELAY_MS, |d| {
            recorded.lock().unwrap().push(d.as_millis() as u64);
        });
        assert_eq!(out.unwrap_err(), "mock exhausted");
        assert_eq!(mock.calls.load(Ordering::SeqCst), MAX_RETRIES as usize);
        assert_eq!(recorded.lock().unwrap().as_slice(), &[300, 600]);
    }

    #[test]
    fn companion_messages_assemble_all_templates() {
        let sys = "全局人设";
        for (tpl, keyword) in [
            ("general", "通俗解读"),
            ("logic", "逻辑链条"),
            ("critical", "批判审视"),
            ("term", "术语拆解"),
        ] {
            let msgs = build_companion_messages(tpl, "选中文本内容", "什么是X?", sys);
            assert_eq!(msgs.len(), 2);
            assert_eq!(msgs[0].role, "system");
            assert!(msgs[0].content.contains(sys), "system 应包含全局人设");
            assert!(msgs[0].content.contains(keyword), "模板 {} 应包含其指令关键词", tpl);
            assert_eq!(msgs[1].role, "user");
            assert!(msgs[1].content.contains("选中文本内容"));
            assert!(msgs[1].content.contains("什么是X?"), "追问应拼入 user 消息");
        }
        // 无追问时不拼追问段
        let msgs = build_companion_messages("general", "选中文本", "", "");
        assert!(!msgs[1].content.contains("我的追问"));
    }

    #[test]
    fn unknown_template_falls_back_to_general_instruction() {
        let msgs = build_companion_messages("mystery", "文本", "", "");
        assert!(msgs[0].content.contains("通俗解读"));
    }

    /// 本地假 OpenAI 服务器：验证请求头（Bearer）与响应解析（choices[0].message.content）。
    #[test]
    fn ureq_client_sends_auth_and_parses_content() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = std::thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            let mut reader = std::io::BufReader::new(stream.try_clone().unwrap());
            let mut request_line = String::new();
            std::io::BufRead::read_line(&mut reader, &mut request_line).unwrap();
            let mut auth_seen = false;
            loop {
                let mut line = String::new();
                std::io::BufRead::read_line(&mut reader, &mut line).unwrap();
                if line.trim().is_empty() {
                    break;
                }
                if line.to_ascii_lowercase().starts_with("authorization:") {
                    auth_seen = line.contains("Bearer sk-local-test");
                }
            }
            assert!(request_line.starts_with("POST /v1/chat/completions"), "请求行: {}", request_line);
            assert!(auth_seen, "应携带 Bearer 鉴权头");
            let body = r#"{"choices":[{"message":{"role":"assistant","content":"本地假服务器回复"}}]}"#;
            let http = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            use std::io::Write;
            let mut stream = stream;
            stream.write_all(http.as_bytes()).unwrap();
        });

        let cfg = serde_json::from_value(json!({
            "endpoint": format!("http://127.0.0.1:{}/v1", port),
            "api_key": "sk-local-test",
            "model_name": "local-model"
        }))
        .unwrap();
        let msgs = build_companion_messages("general", "文本", "", "");
        let out = UreqLlmClient.chat(&cfg, &msgs).expect("本地假服务器应成功返回");
        assert_eq!(out, "本地假服务器回复");
        server.join().unwrap();
    }

    #[test]
    fn ureq_client_surfaces_http_error_as_err() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = std::thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            use std::io::Write;
            let mut stream = stream;
            stream
                .write_all(b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                .unwrap();
        });
        let cfg = serde_json::from_value(json!({
            "endpoint": format!("http://127.0.0.1:{}", port),
            "api_key": "bad-key"
        }))
        .unwrap();
        let out = UreqLlmClient.chat(&cfg, &[]);
        assert!(out.is_err(), "401 应转为 Err 而非 panic");
        server.join().unwrap();
    }
}
