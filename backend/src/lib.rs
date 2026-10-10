// backend/src/lib.rs
// AI Reader Core Crate Root

pub mod domain;
pub mod storage;
pub mod parser;
pub mod nlp;
pub mod service;
pub mod ffi;

pub use ffi::{ai_reader_invoke, ai_reader_free_string, dispatch_invoke, execute_action};
pub use service::ReaderService;
pub use storage::SqliteStorage;
