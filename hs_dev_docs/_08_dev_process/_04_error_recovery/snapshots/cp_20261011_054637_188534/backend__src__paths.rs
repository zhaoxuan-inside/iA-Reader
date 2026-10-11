// backend/src/paths.rs
// 运行期产物集中存储（ADR_005）：
//   base = 环境变量 AI_READER_HOME（非空） > $HOME/.ai-reader
//   <base>/{config,data,logs,books}
// 配置文件可选键 data_dir/log_dir/books_dir 重定位对应分区（进程启动时应用）。
// 旧位置（CWD/HOME 的 ai_reader_data.db、~/.local/share/ai-reader、~/.config/ai-reader）
// 幂等迁移：只复制不删除。

use serde_json::Value;
use std::path::{Path, PathBuf};

/// base 目录解析：env 覆盖优先，默认 HOME/.ai-reader（纯函数，便于测试）。
pub fn resolve_base(env_home: Option<&str>, home: Option<&Path>) -> PathBuf {
    if let Some(v) = env_home {
        let v = v.trim();
        if !v.is_empty() {
            return PathBuf::from(v);
        }
    }
    let h = home.map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    h.join(".ai-reader")
}

/// 进程运行时的 base 目录。
pub fn base_dir() -> PathBuf {
    resolve_base(
        std::env::var("AI_READER_HOME").ok().as_deref(),
        std::env::var("HOME").ok().map(PathBuf::from).as_deref(),
    )
}

/// base 下的 LLM 用户配置路径（固定 config/llm_config.json，不做重定位）。
pub fn llm_config_path(base: &Path) -> PathBuf {
    base.join("config").join("llm_config.json")
}

/// 从 llm_config.json 原始 JSON 提取可选重定位键（data_dir/log_dir/books_dir），
/// 缺省回落 base 派生路径。
pub fn dirs_from_config(
    config_json: Option<&Value>,
    base: &Path,
) -> (PathBuf, PathBuf, PathBuf) {
    let get = |key: &str| -> Option<PathBuf> {
        config_json
            .and_then(|v| v.get(key))
            .and_then(|v| v.as_str())
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(PathBuf::from)
    };
    (
        get("data_dir").unwrap_or_else(|| base.join("data")),
        get("log_dir").unwrap_or_else(|| base.join("logs")),
        get("books_dir").unwrap_or_else(|| base.join("books")),
    )
}

/// 幂等迁移：old 存在且 new 不存在 → 创建目录并复制，返回 true；否则 no-op 返回 false。
pub fn migrate_file(old: &Path, new: &Path) -> std::io::Result<bool> {
    if old.is_file() && !new.exists() {
        if let Some(parent) = new.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::copy(old, new)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

pub struct RuntimePaths {
    pub base: PathBuf,
    pub data_dir: PathBuf,
    pub log_dir: PathBuf,
    pub books_dir: PathBuf,
    pub llm_config_path: PathBuf,
    pub db_path: PathBuf,
    pub migrated: Vec<String>,
}

/// 引擎初始化：迁移旧配置 → 读重定位键 → 建目录 → 初始化文件日志 → 迁移旧 db。
/// 幂等；失败不 panic（目录创建失败等静默回退，由日志观察）。
pub fn init_runtime() -> RuntimePaths {
    let base = base_dir();

    // 1) 旧 LLM 配置迁移（新位置缺失时从 ~/.config/ai-reader 复制）
    let config_path = llm_config_path(&base);
    let mut migrated = Vec::new();
    if !config_path.exists() {
        if let Some(home) = std::env::var("HOME").ok().map(PathBuf::from) {
            let legacy = home.join(".config").join("ai-reader").join("llm_config.json");
            if migrate_file(&legacy, &config_path).unwrap_or(false) {
                migrated.push(format!("config {}", legacy.display()));
            }
        }
    }

    // 2) 读取重定位键（迁移后读，legacy 配置中的覆盖键同样生效）
    let cfg_val = std::fs::read_to_string(&config_path)
        .ok()
        .and_then(|t| serde_json::from_str::<Value>(&t).ok());
    let (data_dir, log_dir, books_dir) = dirs_from_config(cfg_val.as_ref(), &base);

    // 3) 建目录 + 初始化文件日志
    for d in [&data_dir, &log_dir, &books_dir, config_path.parent().unwrap_or(&base)] {
        let _ = std::fs::create_dir_all(d);
    }
    crate::log::init(&log_dir);

    // 4) 旧 db 迁移：HOME > CWD > ~/.local/share 顺序，首个命中者
    let db_path = data_dir.join("ai_reader.db");
    if !db_path.exists() {
        let mut candidates: Vec<PathBuf> = Vec::new();
        if let Some(home) = std::env::var("HOME").ok().map(PathBuf::from) {
            candidates.push(home.join("ai_reader_data.db"));
            candidates.push(home.join(".local/share/ai-reader/ai_reader_data.db"));
        }
        candidates.push(PathBuf::from("ai_reader_data.db"));
        for old in candidates {
            if migrate_file(&old, &db_path).unwrap_or(false) {
                migrated.push(format!("db {}", old.display()));
                break;
            }
        }
    }

    for m in &migrated {
        crate::log::info(&format!("[PATHS] migrated {} -> 当前运行时", m));
    }
    crate::log::info(&format!(
        "[PATHS] runtime base={} data={} logs={} books={}",
        base.display(),
        data_dir.display(),
        log_dir.display(),
        books_dir.display()
    ));

    RuntimePaths {
        base,
        data_dir,
        log_dir,
        books_dir,
        llm_config_path: config_path,
        db_path,
        migrated,
    }
}

/// 进程级运行时路径（get_service 与 doc_parse 共享；首次访问即初始化）。
pub fn runtime() -> &'static RuntimePaths {
    static RUNTIME: std::sync::OnceLock<RuntimePaths> = std::sync::OnceLock::new();
    RUNTIME.get_or_init(init_runtime)
}

/// 导入文档稳定副本：读源文件 → SHA-256 命名写入 books_dir，返回副本路径。
/// 读文件失败即失败（调用方降级沿用原路径）。
pub fn copy_into_books(books_dir: &Path, source: &Path, ext: &str) -> Result<PathBuf, String> {
    let bytes = std::fs::read(source).map_err(|e| format!("读取源文件失败: {}", e))?;
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    let name = format!("{:x}.{}", hasher.finalize(), ext);
    std::fs::create_dir_all(books_dir).map_err(|e| format!("创建 books 目录失败: {}", e))?;
    let dest = books_dir.join(name);
    std::fs::write(&dest, &bytes).map_err(|e| format!("写入副本失败: {}", e))?;
    Ok(dest)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;

    fn temp_root(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!(
            "ai_reader_paths_{}_{}",
            tag,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn resolve_base_prefers_env_override() {
        let home = temp_root("home");
        let out = resolve_base(Some("  /custom/ai-home  "), Some(&home));
        assert_eq!(out, PathBuf::from("/custom/ai-home"), "非空 env 应优先并去空白");
        let out2 = resolve_base(Some(""), Some(&home));
        assert_eq!(out2, home.join(".ai-reader"), "空 env 回落默认");
        let out3 = resolve_base(None, Some(&home));
        assert_eq!(out3, home.join(".ai-reader"));
    }

    #[test]
    fn migrate_file_is_idempotent() {
        let root = temp_root("migrate");
        let old = root.join("old.db");
        fs::write(&old, b"legacy-bytes").unwrap();
        let new = root.join("data/ai_reader.db");

        assert!(migrate_file(&old, &new).unwrap(), "首次应复制");
        assert_eq!(fs::read(&new).unwrap(), b"legacy-bytes");

        // 目标已存在：不覆盖
        fs::write(&new, b"newer-bytes").unwrap();
        assert!(!migrate_file(&old, &new).unwrap());
        assert_eq!(fs::read(&new).unwrap(), b"newer-bytes");

        // 源不存在：no-op
        assert!(!migrate_file(&root.join("nope.db"), &root.join("x.db")).unwrap());
    }

    #[test]
    fn dirs_from_config_applies_overrides() {
        let base = temp_root("dirs");
        let (d, l, b) = dirs_from_config(None, &base);
        assert_eq!(d, base.join("data"));
        assert_eq!(l, base.join("logs"));
        assert_eq!(b, base.join("books"));

        let cfg = json!({
            "data_dir": "/tmp/ai-data-x",
            "log_dir": "/tmp/ai-logs-x",
            "api_key": "sk-x"
        });
        let (d, l, b) = dirs_from_config(Some(&cfg), &base);
        assert_eq!(d, PathBuf::from("/tmp/ai-data-x"), "data_dir 键应重定位");
        assert_eq!(l, PathBuf::from("/tmp/ai-logs-x"), "log_dir 键应重定位");
        assert_eq!(b, base.join("books"), "未设置的键回落默认");

        // 空串视为未设置
        let cfg_empty = json!({"data_dir": ""});
        let (d, _, _) = dirs_from_config(Some(&cfg_empty), &base);
        assert_eq!(d, base.join("data"));
    }

    #[test]
    fn init_runtime_migrates_legacy_db_and_config() {
        let home = temp_root("rt_home");
        // 旧 db（HOME 命中，优先于 CWD/XDG）与旧配置
        fs::write(home.join("ai_reader_data.db"), b"legacy-db").unwrap();
        let legacy_cfg_dir = home.join(".config/ai-reader");
        fs::create_dir_all(&legacy_cfg_dir).unwrap();
        fs::write(legacy_cfg_dir.join("llm_config.json"), r#"{"api_key":"sk-legacy"}"#).unwrap();

        // 保存并恢复环境变量（env 为进程全局，测试后必须还原）
        let saved_home = std::env::var("HOME").ok();
        let saved_env_base = std::env::var("AI_READER_HOME").ok();
        std::env::set_var("AI_READER_HOME", home.join(".ai-reader"));
        std::env::set_var("HOME", &home);
        let rt = init_runtime();
        let rt2 = init_runtime();
        match (saved_home, saved_env_base) {
            (h, b) => {
                if let Some(h) = h { std::env::set_var("HOME", h); }
                match b {
                    Some(b) => std::env::set_var("AI_READER_HOME", b),
                    None => std::env::remove_var("AI_READER_HOME"),
                }
            }
        }

        let base = home.join(".ai-reader");
        assert_eq!(rt.base, base);
        assert!(rt.llm_config_path.exists(), "旧配置应迁移到新位置");
        let migrated_cfg = fs::read_to_string(&rt.llm_config_path).unwrap();
        assert!(migrated_cfg.contains("sk-legacy"));
        assert!(rt.db_path.exists(), "旧 db 应迁移到 <base>/data/ai_reader.db");
        assert_eq!(fs::read(&rt.db_path).unwrap(), b"legacy-db");
        assert!(rt.migrated.len() >= 2, "迁移清单应记录，实际: {:?}", rt.migrated);

        // 幂等：二次 init 不重复迁移（migrated 为空）
        assert!(rt2.migrated.is_empty(), "二次初始化不应再迁移");
        fs::remove_dir_all(&home).ok();
    }

    #[test]
    fn copy_into_books_uses_sha256_name_and_is_stable() {
        let root = temp_root("books");
        let src = root.join("my_book.md");
        fs::write(&src, b"# hello ai-reader").unwrap();

        let books = root.join("books");
        let copy1 = copy_into_books(&books, &src, "md").unwrap();
        assert!(copy1.starts_with(&books));
        assert!(copy1.extension().unwrap() == "md");
        assert_eq!(fs::read(&copy1).unwrap(), b"# hello ai-reader");

        // 同内容再导：sha256 同名，覆盖后内容一致（幂等稳定）
        let copy2 = copy_into_books(&books, &src, "md").unwrap();
        assert_eq!(copy1, copy2);

        // 源不存在 → Err
        assert!(copy_into_books(&books, &root.join("nope.md"), "md").is_err());
        // 名称形如 64 位 hex
        let stem = copy1.file_stem().unwrap().to_string_lossy().to_string();
        assert_eq!(stem.len(), 64, "应为 sha256 hex，实际: {}", stem);
    }
}
