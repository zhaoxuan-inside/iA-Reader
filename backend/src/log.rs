// backend/src/log.rs
// 引擎文件日志（ADR_005）：追加写 <base>/logs/ai_reader.log，stdout/stderr 同步镜像。
// 未初始化（如纯单元测试环境）时仅 stdout，不落盘。

use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;
use std::sync::{Mutex, OnceLock};

static LOG_FILE: OnceLock<Option<Mutex<std::fs::File>>> = OnceLock::new();

/// 初始化文件日志（追加写）。失败时静默降级为仅 stdout。
pub fn init(log_dir: &Path) {
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_dir.join("ai_reader.log"))
        .ok();
    let _ = LOG_FILE.set(file.map(Mutex::new));
}

/// 写一条日志：时间戳 + 级别 + 消息；ERROR 走 stderr，其余走 stdout。
pub fn log(level: &str, msg: &str) {
    let line = format!(
        "[{}] [{}] {}",
        chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f"),
        level,
        msg
    );
    match level {
        "ERROR" => eprintln!("{}", line),
        _ => println!("{}", line),
    }
    if let Some(mutex) = LOG_FILE.get() {
        if let Some(file) = mutex.as_ref() {
            if let Ok(mut f) = file.lock() {
                let _ = writeln!(f, "{}", line);
            }
        }
    }
}

pub fn info(msg: &str) {
    log("INFO", msg);
}

pub fn warn(msg: &str) {
    log("WARN", msg);
}

pub fn error(msg: &str) {
    log("ERROR", msg);
}

#[macro_export]
macro_rules! log_info {
    ($($arg:tt)*) => { $crate::log::info(&format!($($arg)*)) };
}

#[macro_export]
macro_rules! log_warn {
    ($($arg:tt)*) => { $crate::log::warn(&format!($($arg)*)) };
}

#[macro_export]
macro_rules! log_error {
    ($($arg:tt)*) => { $crate::log::error(&format!($($arg)*)) };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn log_writes_timestamped_line_to_file() {
        let dir = std::env::temp_dir().join(format!(
            "ai_reader_log_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        init(&dir);
        info("hello paths");
        error("boom");
        let text = std::fs::read_to_string(dir.join("ai_reader.log")).unwrap();
        assert!(text.contains("[INFO] hello paths"));
        assert!(text.contains("[ERROR] boom"));
        assert!(text.contains("[20"), "应包含时间戳年份");
        std::fs::remove_dir_all(&dir).ok();
    }
}
