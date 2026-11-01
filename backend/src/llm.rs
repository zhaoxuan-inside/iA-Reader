// backend/src/llm.rs
// LLM 认知伴读客户端：配置读取（与 Python 引擎同构）+ OpenAI 兼容 chat/completions + 指数退避重试
//
// Seam 约定（见 task_06 任务详情）：
// - `LlmConfig::load_from`  : 配置合并优先级 用户 > 默认文件 > 内建缺省
// - `LlmClient::chat`       : 可替换的传输层（生产 UreqLlmClient / 测试 Mock）
// - `chat_with_retry`       : 指数退避重试编排（sleep 可注入，测试零真实等待）
// - `build_companion_messages`: 4 大认知模板 prompt 组装

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::io::BufRead;
use std::time::Duration;

/// 重试次数缺省值（含首次调用），对齐 PRD §4.1「指数退避重试（最多 3 次）」；
/// 实际取值来自配置 max_retries（0~5 可配）
pub const MAX_RETRIES: u32 = 3;
/// 退避基础延时（毫秒），第 n 次重试前等待 base * 2^(n-1)
pub const BASE_DELAY_MS: u64 = 300;
/// 单次请求超时缺省值（毫秒），配置 timeout_ms 可在 1000~120000 间调整
pub const DEFAULT_TIMEOUT_MS: u64 = 60_000;

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

/// LLM 配置：`<base>/config/llm_config.json` 为唯一用户配置源（密钥密文单独存储）。
#[derive(Debug, Clone, Serialize, Deserialize)]
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
    /// 单次请求超时（毫秒），FEAT-006 §3 要求可配
    #[serde(default = "default_timeout_ms")]
    pub timeout_ms: u64,
    /// 重试次数（0~5），FEAT-006 §3 要求可配
    #[serde(default = "default_max_retries")]
    pub max_retries: u32,
}

fn default_timeout_ms() -> u64 {
    DEFAULT_TIMEOUT_MS
}
fn default_max_retries() -> u32 {
    MAX_RETRIES
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
/// `Send + Sync` 约束：ReaderService 以 &'static 直接共享（ffi.rs 全局单例），
/// 跨线程并发调用要求传输层既可移动又可共享。
pub trait LlmClient: Send + Sync {
    fn chat(&self, config: &LlmConfig, messages: &[ChatMessage]) -> Result<String, String>;

    /// 流式生成（task_17 D1）：on_delta 逐段回调，返回完整文本。
    /// 默认实现降级为一次性整段回调——既有 Mock/测试零改动即可接入流式管线。
    fn chat_stream(
        &self,
        config: &LlmConfig,
        messages: &[ChatMessage],
        on_delta: &mut dyn FnMut(&str),
    ) -> Result<String, String> {
        let content = self.chat(config, messages)?;
        on_delta(&content);
        Ok(content)
    }
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

    /// 真实配置解析：用户配置 `<base>/config/llm_config.json`（与 config.save 写入路径
    /// 同源，ADR_005 集中存储）；旧版位置 `~/.config/ai-reader/llm_config.json` 仅作回退，
    /// 保住升级用户已存密钥。默认配置 `<workspace>/config/default_llm_config.json`
    /// 仅存在于开发/源码环境。
    /// 此前 load 读旧版位置而 save 写集中存储位置——设置保存后重载读不回（重启丢配置）。
    pub fn load() -> LlmConfig {
        let base_cfg = crate::paths::llm_config_path(&crate::paths::base_dir());
        let legacy = std::env::var("HOME").ok().map(|h| {
            Path::new(&h).join(".config").join("ai-reader").join("llm_config.json")
        });
        let user = if base_cfg.exists() {
            Some(base_cfg)
        } else {
            legacy.filter(|p| p.exists())
        };
        let default_path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("config")
            .join("default_llm_config.json");
        let default = if default_path.exists() { Some(default_path) } else { None };
        let mut cfg = Self::load_from(user.as_deref(), default.as_deref());
        // 明文 JSON 未携带密钥时从密文文件解密补齐（save_user_config 的对偶路径）；
        // 老版本明文密钥走 load_from 已带回，下次保存自动迁移为密文
        if cfg.api_key.trim().is_empty() {
            if let Ok(blob) = std::fs::read_to_string(api_key_secret_path()) {
                let plain = decrypt_api_key_with(&keystone_path(), &blob);
                if !plain.is_empty() {
                    cfg.api_key = plain;
                }
            }
        }
        cfg
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
    build_companion_messages_with_history(template_type, selected_text, prompt, system_prompt, &[])
}

/// 多轮版本（FEAT-005 REQ-003「追问上下文连续」）：history 为既往轮次
/// （用户输入, 助手回复），按序插入 system 与本轮 user 之间——
/// 此前每次只组 system+单条 user，追问等效于无状态重发选区。
pub fn build_companion_messages_with_history(
    template_type: &str,
    selected_text: &str,
    prompt: &str,
    system_prompt: &str,
    history: &[(String, String)],
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

    let mut msgs = Vec::with_capacity(history.len() * 2 + 2);
    msgs.push(ChatMessage { role: "system", content: system });
    for (u, a) in history {
        msgs.push(ChatMessage { role: "user", content: u.clone() });
        msgs.push(ChatMessage { role: "assistant", content: a.clone() });
    }
    msgs.push(ChatMessage { role: "user", content: user });
    msgs
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

/// 流式重试包装（task_17 D1）：重试语义与 chat_with_retry 一致。
/// 注意：某次尝试中途失败时已推送的 delta 不可撤回，下一次成功尝试的增量会继续追加；
/// 终态以返回全文（落库与 poll 终值）为权威覆盖，短暂重复由终态收敛。
pub fn chat_with_retry_stream<S>(
    client: &dyn LlmClient,
    config: &LlmConfig,
    messages: &[ChatMessage],
    max_retries: u32,
    base_delay_ms: u64,
    sleep: S,
    on_delta: &mut dyn FnMut(&str),
) -> Result<String, String>
where
    S: Fn(Duration),
{
    let mut attempt: u32 = 0;
    loop {
        match client.chat_stream(config, messages, on_delta) {
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

fn request_timeout(config: &LlmConfig) -> Duration {
    Duration::from_millis(config.timeout_ms.clamp(1_000, 120_000))
}

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
            .timeout(request_timeout(config))
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

    /// SSE 流式（task_17 D1）：OpenAI 兼容 `data:` 帧 + `[DONE]` 终止。
    fn chat_stream(
        &self,
        config: &LlmConfig,
        messages: &[ChatMessage],
        on_delta: &mut dyn FnMut(&str),
    ) -> Result<String, String> {
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
            "stream": true,
        });

        let resp = ureq::post(&url)
            .set("Authorization", &format!("Bearer {}", config.api_key.trim()))
            .timeout(request_timeout(config))
            .send_json(body)
            .map_err(|e| format!("LLM stream request failed: {}", e))?;

        let reader = resp.into_reader();
        let mut full = String::new();
        for line in std::io::BufReader::new(reader).lines() {
            let line = line.map_err(|e| format!("LLM stream read failed: {}", e))?;
            if let Some(delta) = parse_sse_delta_line(&line) {
                if !delta.is_empty() {
                    on_delta(&delta);
                    full.push_str(&delta);
                }
            }
        }
        if full.is_empty() {
            return Err("LLM stream produced no content".to_string());
        }
        Ok(full)
    }
}

/// SSE 帧行解析（task_17 D1 纯函数）：`data: {...}` → `choices[0].delta.content`；
/// `data: [DONE]` 与空行/注释行返回 None。
fn parse_sse_delta_line(line: &str) -> Option<String> {
    let payload = line.strip_prefix("data:")?.trim();
    if payload.is_empty() || payload == "[DONE]" {
        return None;
    }
    let value: Value = serde_json::from_str(payload).ok()?;
    value
        .get("choices")
        .and_then(|c| c.get(0))
        .and_then(|c| c.get("delta"))
        .and_then(|d| d.get("content"))
        .and_then(|c| c.as_str())
        .map(|s| s.to_string())
}

// =========================================================================
// 设置页配置能力 (task_07)：路径 / 校验 / 保存 / 合并 / 连接测试
// =========================================================================

/// 用户级配置文件路径（与 Python CLI 引擎共享同一份；ADR_005 集中存储）。
pub fn user_config_path() -> std::path::PathBuf {
    crate::paths::llm_config_path(&crate::paths::base_dir())
}

/// 配置合法性校验：endpoint 协议、temperature 与 max_output_tokens 范围。
pub fn validate_config(cfg: &LlmConfig) -> Result<(), String> {
    if !(cfg.endpoint.starts_with("http://") || cfg.endpoint.starts_with("https://")) {
        return Err(format!("endpoint 必须以 http:// 或 https:// 开头，当前: {}", cfg.endpoint));
    }
    if !(0.0..=2.0).contains(&cfg.temperature) {
        return Err(format!("temperature 必须在 0.0 ~ 2.0 之间，当前: {}", cfg.temperature));
    }
    if !(1..=8192).contains(&cfg.max_output_tokens) {
        return Err(format!("max_output_tokens 必须在 1 ~ 8192 之间，当前: {}", cfg.max_output_tokens));
    }
    if !(1000..=120_000).contains(&cfg.timeout_ms) {
        return Err(format!("timeout_ms 必须在 1000 ~ 120000 之间，当前: {}", cfg.timeout_ms));
    }
    if cfg.max_retries > 5 {
        return Err(format!("max_retries 必须在 0 ~ 5 之间，当前: {}", cfg.max_retries));
    }
    Ok(())
}

// =========================================================================
// api_key 本地加密存储（AES-256-GCM）
// =========================================================================
// 密文落 <base>/config/llm_secret，主密钥落 <base>/config/.keystone（0600）。
// 此前 api_key 以明文 JSON 落盘；加密不能对抗同用户进程，但可挡住字符串扫描、
// 误同步与打包收集——本地威胁模型下是配置文件形态里最务实的保护。

use aes_gcm::aead::Aead;
use aes_gcm::{Aes256Gcm, KeyInit, Nonce};

pub fn keystone_path() -> PathBuf {
    user_config_path().with_file_name(".keystone")
}

pub fn api_key_secret_path() -> PathBuf {
    user_config_path().with_file_name("llm_secret")
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn hex_decode(text: &str) -> Result<Vec<u8>, String> {
    if !text.len().is_multiple_of(2) {
        return Err("hex 长度非法".to_string());
    }
    (0..text.len() / 2)
        .map(|i| u8::from_str_radix(&text[i * 2..i * 2 + 2], 16).map_err(|e| e.to_string()))
        .collect()
}

fn restrict_permissions(path: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))
            .map_err(|e| format!("收紧文件权限失败 {}: {}", path.display(), e))?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}

/// 读取（或首次生成）本机主密钥：32 字节随机值，hex 存储，0600 权限
fn load_or_create_keystone_at(path: &Path) -> Result<[u8; 32], String> {
    if path.exists() {
        let text = std::fs::read_to_string(path).map_err(|e| format!("读取主密钥失败: {}", e))?;
        let bytes = hex_decode(text.trim())?;
        let mut key = [0u8; 32];
        if bytes.len() != 32 {
            return Err("主密钥长度非法".to_string());
        }
        key.copy_from_slice(&bytes);
        return Ok(key);
    }
    let parent = path.parent().ok_or_else(|| format!("主密钥路径非法: {}", path.display()))?;
    std::fs::create_dir_all(parent).map_err(|e| format!("创建配置目录失败: {}", e))?;
    let mut key = [0u8; 32];
    use rand::Rng;
    rand::rng().fill_bytes(&mut key);
    std::fs::write(path, hex_encode(&key)).map_err(|e| format!("写入主密钥失败: {}", e))?;
    restrict_permissions(path)?;
    Ok(key)
}

/// api_key → hex(nonce || AES-GCM 密文)
fn encrypt_api_key_with(keystone: &Path, plain: &str) -> Result<String, String> {
    use rand::Rng;
    let key = load_or_create_keystone_at(keystone)?;
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|e| format!("密钥初始化失败: {}", e))?;
    let mut nonce_bytes = [0u8; 12];
    rand::rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::try_from(&nonce_bytes[..]).map_err(|e| format!("nonce 初始化失败: {:?}", e))?;
    let ct = cipher
        .encrypt(&nonce, plain.as_bytes())
        .map_err(|e| format!("密钥加密失败: {}", e))?;
    let mut blob = nonce_bytes.to_vec();
    blob.extend_from_slice(&ct);
    Ok(hex_encode(&blob))
}

/// hex(nonce || 密文) → api_key；任何失败返回空串（配置缺失/损坏时按未配置处理，不致命）
fn decrypt_api_key_with(keystone: &Path, blob: &str) -> String {
    let decoded = match hex_decode(blob.trim()) {
        Ok(v) if v.len() > 12 => v,
        _ => return String::new(),
    };
    let Ok(key) = load_or_create_keystone_at(keystone) else {
        return String::new();
    };
    let Ok(cipher) = Aes256Gcm::new_from_slice(&key) else {
        return String::new();
    };
    let (nonce, ct) = decoded.split_at(12);
    match Nonce::try_from(nonce) {
        Ok(n) => cipher
            .decrypt(&n, ct)
            .ok()
            .and_then(|v| String::from_utf8(v).ok())
            .unwrap_or_default(),
        Err(_) => String::new(),
    }
}

/// 保存用户级配置：校验 → api_key 加密写密文文件（0600）→ 主配置 JSON 不含明文密钥。
/// 老版本遗留的明文 api_key 在下次保存时自动迁移为密文形态。
pub fn save_user_config(path: &Path, cfg: &LlmConfig) -> Result<(), String> {
    validate_config(cfg)?;
    let parent = path.parent().ok_or_else(|| format!("配置路径非法: {}", path.display()))?;
    std::fs::create_dir_all(parent).map_err(|e| format!("创建配置目录失败: {}", e))?;

    // 密钥出 JSON：非空写密文文件（与传入配置同目录），空则清掉旧密文（用户显式清空密钥）
    let keystone = path.with_file_name(".keystone");
    let secret = path.with_file_name("llm_secret");
    if cfg.api_key.trim().is_empty() {
        std::fs::remove_file(&secret).ok();
    } else {
        let blob = encrypt_api_key_with(&keystone, cfg.api_key.trim())?;
        std::fs::write(&secret, blob).map_err(|e| format!("写入密钥密文失败: {}", e))?;
        restrict_permissions(&secret)?;
    }

    let mut on_disk = cfg.clone();
    on_disk.api_key = String::new();
    let text = serde_json::to_string_pretty(&on_disk).map_err(|e| format!("配置序列化失败: {}", e))?;
    std::fs::write(path, text).map_err(|e| format!("写入配置失败: {}", e))
}

/// 键级 merge：patch 覆盖 base 同名字段，缺省字段回落基线（语义对齐 Python dict.update）。
/// 特判：api_key 等于掩码占位（前端未修改的回显值）时保留基线真实密钥，
/// 防止把 "********" 落盘顶掉真密钥。
pub fn overlay_config(base: &LlmConfig, patch: Option<&Value>) -> Result<LlmConfig, String> {
    let mut merged = serde_json::to_value(base).map_err(|e| format!("基线配置序列化失败: {}", e))?;
    if let Some(Value::Object(map)) = patch {
        let obj = merged.as_object_mut().ok_or("基线配置不是 JSON 对象")?;
        for (k, v) in map {
            if k == "api_key" && v.as_str() == Some(API_KEY_MASK) {
                continue;
            }
            obj.insert(k.clone(), v.clone());
        }
    }
    serde_json::from_value(merged).map_err(|e| format!("配置字段非法: {}", e))
}

/// api_key 回显掩码（PRD NFR「密钥不回显明文」：真实值仅存本机配置文件，
/// 不进入 config.get 等任何返回通道）
pub const API_KEY_MASK: &str = "********";

/// 尾号提示：设置界面显示「已配置（尾号 abcd）」用，不泄露可复原信息
pub fn api_key_tail(cfg: &LlmConfig) -> String {
    cfg.api_key.chars().rev().take(4).collect::<Vec<_>>().into_iter().rev().collect()
}

/// 连接测试：单次真实调用（不重试），返回时延毫秒；无 key 直接拒绝，错误信息透传 UI。
pub fn test_llm_connection(client: &dyn LlmClient, config: &LlmConfig) -> Result<u128, String> {
    if config.api_key.trim().is_empty() {
        return Err("api_key 未配置，请先填写 API Key".to_string());
    }
    let messages = vec![
        ChatMessage { role: "system", content: "You are a connection test assistant.".to_string() },
        ChatMessage { role: "user", content: "ping".to_string() },
    ];
    let start = std::time::Instant::now();
    client.chat(config, &messages)?;
    Ok(start.elapsed().as_millis())
}

#[cfg(test)]
pub mod tests {
    #[test]
    fn parse_sse_delta_line_cases() {
        assert_eq!(
            parse_sse_delta_line("data: {\"choices\":[{\"delta\":{\"content\":\"你好\"}}]}"),
            Some("你好".to_string())
        );
        assert_eq!(parse_sse_delta_line("data: [DONE]"), None);
        assert_eq!(parse_sse_delta_line("data: "), None);
        assert_eq!(parse_sse_delta_line(": keep-alive"), None);
        assert_eq!(parse_sse_delta_line("data: not-json"), None);
    }

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
    // ==================== config 设置页能力 (task_07) ====================

    fn temp_dir_path(tag: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "ai_reader_llm_cfg_{}_{}",
            tag,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
    }

    #[test]
    fn save_user_config_roundtrip() {
        let path = temp_dir_path("roundtrip").join("llm_config.json");
        let cfg = serde_json::from_value(json!({
            "endpoint": "https://api.test.com/v1",
            "api_key": "sk-roundtrip",
            "model_name": "m1",
            "temperature": 0.3,
            "max_output_tokens": 1024,
            "system_prompt": "人设A"
        }))
        .unwrap();
        save_user_config(&path, &cfg).unwrap();
        // 新契约：JSON 不落明文，load_from 只回 JSON 形态（api_key 空）
        let loaded = LlmConfig::load_from(Some(&path), None);
        assert!(loaded.api_key.is_empty(), "JSON 形态不回明文密钥");
        let blob = std::fs::read_to_string(path.with_file_name("llm_secret")).unwrap();
        assert_eq!(
            decrypt_api_key_with(&path.with_file_name(".keystone"), &blob),
            "sk-roundtrip",
            "密文文件应可解密回原密钥"
        );
        assert_eq!(loaded.endpoint, "https://api.test.com/v1");
        assert_eq!(loaded.model_name, "m1");
        assert_eq!(loaded.temperature, 0.3);
        assert_eq!(loaded.max_output_tokens, 1024);
        assert_eq!(loaded.system_prompt, "人设A");
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn save_user_config_creates_missing_dirs() {
        let path = temp_dir_path("dirs").join("a/b/c/llm_config.json");
        let cfg = LlmConfig::default();
        save_user_config(&path, &cfg).unwrap();
        assert!(path.exists(), "多级目录应自动创建");
        std::fs::remove_dir_all(path.parent().unwrap().parent().unwrap().parent().unwrap()).ok();
    }

    #[test]
    fn validate_config_rules() {
        let mut cfg = LlmConfig::default();
        assert!(validate_config(&cfg).is_ok(), "内建缺省应合法");

        cfg.endpoint = "ftp://bad".into();
        assert!(validate_config(&cfg).is_err(), "非 http(s) endpoint 应拒绝");
        cfg.endpoint = "https://ok.example.com/v1".into();

        cfg.temperature = 2.5;
        assert!(validate_config(&cfg).is_err(), "temperature 越界应拒绝");
        cfg.temperature = 0.7;

        cfg.max_output_tokens = 0;
        assert!(validate_config(&cfg).is_err(), "max_output_tokens 下界应拒绝");
        cfg.max_output_tokens = 100000;
        assert!(validate_config(&cfg).is_err(), "max_output_tokens 上界应拒绝");
    }

    #[test]
    fn test_llm_connection_without_key_never_calls_client() {
        let mock = MockLlmClient::new(vec![Ok("不应被调用".to_string())]);
        let calls = mock.calls.clone();
        let cfg = test_config("");
        let out = test_llm_connection(&mock, &cfg);
        assert!(out.is_err());
        assert_eq!(calls.load(Ordering::SeqCst), 0, "无 key 不得发起任何调用");
    }

    #[test]
    fn test_llm_connection_success_reports_latency() {
        let mock = MockLlmClient::new(vec![Ok("pong".to_string())]);
        let calls = mock.calls.clone();
        let cfg = test_config("sk-ok");
        let ms = test_llm_connection(&mock, &cfg).unwrap();
        assert_eq!(calls.load(Ordering::SeqCst), 1, "连接测试只调一次不重试");
        let _ = ms; // 时延数值依赖环境，仅要求可测量（u128 恒非负）
    }

    #[test]
    fn test_llm_connection_failure_propagates_message() {
        let mock = MockLlmClient::new(vec![Err("401 Unauthorized".to_string())]);
        let cfg = test_config("sk-bad");
        let err = test_llm_connection(&mock, &cfg).unwrap_err();
        assert!(err.contains("401"), "错误信息应透传给 UI 展示");
    }

    #[test]
    fn overlay_config_merges_patch_keys() {
        let base = test_config("sk-base");
        let patch = json!({"api_key": "sk-new", "model_name": "new-model"});
        let merged = overlay_config(&base, Some(&patch)).unwrap();
        assert_eq!(merged.api_key, "sk-new");
        assert_eq!(merged.model_name, "new-model");
        assert_eq!(merged.endpoint, base.endpoint, "未覆盖字段保持基线");
        // 无 patch → 原样
        let same = overlay_config(&base, None).unwrap();
        assert_eq!(same.api_key, "sk-base");
    }
}


#[cfg(test)]
mod secret_storage_tests {
    use super::*;

    #[test]
    fn api_key_is_encrypted_at_rest_and_roundtrips() {
        let dir = std::env::temp_dir().join(format!(
            "ai_reader_secret_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let path = dir.join("llm_config.json");
        let cfg = serde_json::from_value(json!({
            "endpoint": "https://api.test.com/v1",
            "api_key": "sk-super-secret-value",
            "model_name": "m1"
        }))
        .unwrap();

        save_user_config(&path, &cfg).unwrap();

        // 主配置 JSON 不含明文密钥
        let on_disk = std::fs::read_to_string(&path).unwrap();
        assert!(!on_disk.contains("sk-super-secret-value"), "JSON 不得含明文密钥: {}", on_disk);
        // 密文文件存在且不含明文
        let secret = path.with_file_name("llm_secret");
        let blob = std::fs::read_to_string(&secret).unwrap();
        assert!(!blob.contains("sk-super-secret-value"), "密文文件不得含明文");
        // 解密回原文
        let keystone = path.with_file_name(".keystone");
        assert_eq!(decrypt_api_key_with(&keystone, &blob), "sk-super-secret-value");
        // 主密钥文件权限 0600（unix）
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mode = std::fs::metadata(&keystone).unwrap().permissions().mode() & 0o777;
            assert_eq!(mode, 0o600, "主密钥文件应为 0600: {:o}", mode);
        }

        // 显式清空密钥 → 密文文件被移除
        let mut cleared = cfg.clone();
        cleared.api_key = String::new();
        save_user_config(&path, &cleared).unwrap();
        assert!(!secret.exists(), "清空密钥后密文文件应移除");

        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn validate_config_checks_timeout_and_retries() {
        let bad_low = LlmConfig { timeout_ms: 500, ..Default::default() };
        assert!(validate_config(&bad_low).is_err(), "timeout_ms 下界应拒绝");
        let bad_high = LlmConfig { timeout_ms: 200_000, ..Default::default() };
        assert!(validate_config(&bad_high).is_err(), "timeout_ms 上界应拒绝");
        let bad_retries = LlmConfig { timeout_ms: 30_000, max_retries: 6, ..Default::default() };
        assert!(validate_config(&bad_retries).is_err(), "max_retries 上界应拒绝");
        let ok = LlmConfig { timeout_ms: 30_000, max_retries: 2, ..Default::default() };
        assert!(validate_config(&ok).is_ok());
    }

    #[test]
    fn companion_messages_with_history_preserves_thread_context() {
        let history = vec![
            ("我先问了个问题".to_string(), "我先答了".to_string()),
        ];
        let msgs = build_companion_messages_with_history("general", "选区", "追问内容", "人设", &history);
        assert_eq!(msgs.len(), 4, "system + (user, assistant) 历史 + 本轮 user");
        assert_eq!(msgs[0].role, "system");
        assert_eq!(msgs[1].role, "user");
        assert_eq!(msgs[2].role, "assistant");
        assert_eq!(msgs[2].content, "我先答了");
        assert!(msgs[3].content.contains("追问内容"));
        // 空历史与旧单发形态等价
        let no_hist = build_companion_messages_with_history("general", "选区", "", "人设", &[]);
        assert_eq!(no_hist.len(), 2);
    }
}
