#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_00_e2e/test_rust_engine_full_flow_e2e.py
Rust 引擎(libreader_core.so)全旅程端到端测试

与 test_reader_full_flow_e2e.py（Python 引擎）形成双引擎对偶：
真实 GUI 运行时经 dart:ffi 加载的正是本测试驱动的 Rust C-ABI 引擎。
覆盖完整用户旅程：导入 → 书库 → 阅读数据（句子绑定真实章节）→
划词伴读（流式降级 + 阻塞降级）→ 批注生命周期 → 导图/词云 →
配置持久化 → 跨进程数据留存（模拟应用重启）。

字段形状契约由 test/_03_contract_test/test_ffi_contract.py 单独钉住，此处不重复。
运行前置：在 backend/ 下执行 cargo build --release。
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def locate_library():
    explicit = os.environ.get("AI_READER_CONTRACT_LIB")
    if explicit:
        return Path(explicit)
    for p in [
        WORKSPACE_ROOT / "backend" / "target" / "release" / "libreader_core.so",
        WORKSPACE_ROOT / "backend" / "target" / "debug" / "libreader_core.so",
    ]:
        if p.exists():
            return p
    return None


LIB_PATH = locate_library()

# 跨进程持久化探针：独立进程加载同一 .so 与同一 AI_READER_HOME，
# 模拟"应用重启后"对书库/批注/配置的读取。
# 结果写文件而非 stdout——引擎日志与 JSON 混流会破坏 stdout 解析。
RESTART_PROBE_SNIPPET = r"""
import ctypes, json, sys
lib = ctypes.CDLL(sys.argv[1])
lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
lib.ai_reader_invoke.restype = ctypes.c_void_p
lib.ai_reader_free_string.argtypes = [ctypes.c_void_p]

def invoke(action, payload):
    ptr = lib.ai_reader_invoke(action.encode(), json.dumps(payload).encode())
    raw = json.loads(ctypes.string_at(ptr).decode())
    lib.ai_reader_free_string(ptr)
    return raw

snapshot = {
    "books": invoke("doc.list", {})["data"]["books"],
    "annotations": invoke("annotation.list", {"book_id": int(sys.argv[2])})["data"]["annotations"],
    "config": invoke("config.get", {})["data"]["config"],
}
with open(sys.argv[3], "w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False)
"""


class TestRustEngineFullFlowE2E(unittest.TestCase):
    """真实 Rust 引擎上的全旅程冒烟（隔离 AI_READER_HOME，不触碰本机真实数据）"""

    lib = None
    home = None
    book_id = None
    first_section_id = None

    @classmethod
    def setUpClass(cls):
        if LIB_PATH is None:
            raise AssertionError(
                "libreader_core.so 未构建：先在 backend/ 执行 cargo build --release"
            )
        cls.home = Path(tempfile.mkdtemp(prefix="ai_reader_e2e_rust_"))
        os.environ["AI_READER_HOME"] = str(cls.home)
        # 连 HOME 一并隔离：引擎对旧版配置位置 ~/.config/ai-reader 有回退读取，
        # 不隔离会把宿主机历史配置泄进测试（全封闭）
        cls._orig_home = os.environ.get("HOME")
        os.environ["HOME"] = str(cls.home)

        cls.lib = ctypes.CDLL(str(LIB_PATH))
        cls.lib.ai_reader_invoke.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        cls.lib.ai_reader_invoke.restype = ctypes.c_void_p
        cls.lib.ai_reader_free_string.argtypes = [ctypes.c_void_p]
        cls.lib.ai_reader_free_string.restype = None

        cls.sample = cls.home / "rust_e2e_sample.md"
        cls.sample.write_text(
            "# 第 1 章 预写式日志\n\n"
            "预写式日志是保证事务原子性与持久性的关键机制。\n"
            "所有修改在落盘前必须先顺序追加到日志。\n\n"
            "# 第 2 章 快照隔离\n\n"
            "快照隔离让读取者绝不阻塞写入者，写入者也绝不阻塞读取者。\n",
            encoding="utf-8",
        )
        code, data, msg, _ = cls.invoke("doc.parse", {"file_path": str(cls.sample)})
        if code != 0:
            raise AssertionError(f"setUpClass 导入样例书失败: {msg}")
        cls.book_id = data["id"]

        _, doc, _, _ = cls.invoke("doc.get", {"book_id": cls.book_id})
        cls.first_section_id = doc["sections"][0]["id"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    @classmethod
    def invoke(cls, action, payload):
        ptr = cls.lib.ai_reader_invoke(
            action.encode("utf-8"), json.dumps(payload).encode("utf-8")
        )
        raw = json.loads(ctypes.string_at(ptr).decode("utf-8"))
        cls.lib.ai_reader_free_string(ptr)
        return raw["code"], raw["data"], raw["message"], raw.get("metrics") or {}

    # ------------------------------------------------------------------
    # 旅程一：导入后的阅读数据就绪（书库 → 章节段落 → 导图 → 词云）
    # ------------------------------------------------------------------
    def test_01_reading_journey_data_ready(self):
        # 书库：真实章节数
        code, data, msg, metrics = self.invoke("doc.list", {})
        self.assertEqual(code, 0, msg)
        self.assertGreater(metrics.get("duration_ms", -1), 0, "六元组信封必须携带 metrics")
        book = next(b for b in data["books"] if b["id"] == self.book_id)
        self.assertEqual(book["sections_count"], 2)

        # 阅读数据：段落来自句子切片且绑定真实章节（此前占位外键只对第一本书碰巧成立）
        code, doc, msg, _ = self.invoke("doc.get", {"book_id": self.book_id})
        self.assertEqual(code, 0, msg)
        self.assertEqual(len(doc["sections"]), 2)
        all_paragraph_ids = []
        for sec in doc["sections"]:
            self.assertTrue(sec["paragraphs"], f"章节[{sec['title']}]段落为空")
            for p in sec["paragraphs"]:
                self.assertTrue(p["text"])
                all_paragraph_ids.append(p["id"])
        self.assertEqual(len(all_paragraph_ids), len(set(all_paragraph_ids)), "段落 id 不得重复")
        joined = "\n".join(p["text"] for sec in doc["sections"] for p in sec["paragraphs"])
        self.assertIn("预写式日志", joined)
        self.assertIn("快照隔离", joined)

        # 导图：根节点 + 章节节点携带 section_id 供跳转
        code, data, msg, _ = self.invoke("mindmap.generate", {"book_id": self.book_id})
        self.assertEqual(code, 0, msg)
        section_nodes = [n for n in data["nodes"] if n["section_id"] is not None]
        self.assertEqual(len(section_nodes), 2, "两个章节应各产生一个导图节点")

        # 词云：离线 NLP 抽取得出关键词
        code, data, msg, _ = self.invoke("nlp.keyword_extract", {"book_id": self.book_id})
        self.assertEqual(code, 0, msg)
        self.assertTrue(data["keywords"], "词云关键词不应为空")

    # ------------------------------------------------------------------
    # 旅程二：划词伴读（主路径流式 start/poll + 兜底阻塞 ask），空密钥走离线降级
    # ------------------------------------------------------------------
    def test_02_companion_streaming_offline_then_ask(self):
        selected = "预写式日志是保证事务原子性与持久性的关键机制"
        code, data, msg, _ = self.invoke("ai.companion_start", {
            "book_id": self.book_id,
            "template_type": "general",
            "selected_text": selected,
        })
        self.assertEqual(code, 0, msg)
        request_id = data["request_id"]
        self.assertTrue(request_id)

        final_partial = ""
        offline = False
        for _ in range(100):
            code, data, msg, _ = self.invoke("ai.companion_poll", {"request_id": request_id})
            self.assertEqual(code, 0, msg)
            final_partial = data.get("partial") or final_partial
            offline = data.get("offline", False)
            if data.get("done"):
                break
            import time
            time.sleep(0.1)
        self.assertTrue(data.get("done"), "流式伴读未在超时内收敛")
        self.assertTrue(offline, "空 api_key 下应标记 offline=true")
        self.assertTrue(
            final_partial.startswith("【离线模式】"),
            f"离线降级卡应带【离线模式】前缀（前端据此显示降级提示）: {final_partial[:50]}",
        )

        # 兜底阻塞契约：老引擎兼容路径
        code, data, msg, _ = self.invoke("ai.companion_ask", {
            "book_id": self.book_id,
            "template_type": "general",
            "selected_text": "快照隔离",
        })
        self.assertEqual(code, 0, msg)
        self.assertIn("快照隔离", data["response"], "启发卡应回显选区文本")
        self.assertEqual(data["template_type"], "general")

    # ------------------------------------------------------------------
    # 旅程三：批注生命周期 save → list → update → list → delete → list
    # ------------------------------------------------------------------
    def test_03_annotation_full_lifecycle(self):
        code, data, msg, _ = self.invoke("annotation.save", {
            "book_id": self.book_id,
            "section_id": self.first_section_id,
            "style": "highlight",
            "color": "#FFE066",
            "note_text": "初始批注",
            "anchor": {"paragraph_id": "p1", "start": 0, "end": 5},
            "ai_response": "【通俗解读】AI 沉淀内容",
        })
        self.assertEqual(code, 0, msg)
        annotation_id = data["annotation_id"]

        code, data, _, _ = self.invoke("annotation.list", {"book_id": self.book_id})
        saved = next(a for a in data["annotations"] if a["id"] == annotation_id)
        self.assertEqual(saved["style"], "highlight")
        self.assertEqual(saved["note_text"], "初始批注")
        self.assertIn("paragraph_id", json.loads(saved["anchor_json"]))

        code, data, msg, _ = self.invoke("annotation.update", {
            "annotation_id": annotation_id,
            "note_text": "更新后的批注",
            "color": "#007AFF",
        })
        self.assertEqual(code, 0, msg)
        self.assertEqual(data["status"], "updated")

        code, data, _, _ = self.invoke("annotation.list", {"book_id": self.book_id})
        updated = next(a for a in data["annotations"] if a["id"] == annotation_id)
        self.assertEqual(updated["note_text"], "更新后的批注")
        self.assertEqual(updated["color"], "#007AFF")

        code, data, msg, _ = self.invoke("annotation.delete", {"annotation_id": annotation_id})
        self.assertEqual(code, 0, msg)
        self.assertEqual(data["status"], "deleted")

        code, data, _, _ = self.invoke("annotation.list", {"book_id": self.book_id})
        self.assertFalse(
            any(a["id"] == annotation_id for a in data["annotations"]),
            "删除后批注不应再出现",
        )

    # ------------------------------------------------------------------
    # 旅程四：LLM 配置三通道——默认加载 → 用户配置保存 → 读回一致
    # ------------------------------------------------------------------
    def test_04_config_roundtrip(self):
        code, data, msg, _ = self.invoke("config.get", {})
        self.assertEqual(code, 0, msg)
        cfg = data["config"]
        self.assertEqual(cfg["endpoint"], "https://api.deepseek.com/v1", "应从内置默认/默认文件加载")
        self.assertEqual(cfg["api_key"], "", "隔离 HOME 首启 api_key 应为空")

        code, data, msg, _ = self.invoke("config.save", {
            "config": {"api_key": "sk-e2e-.roundtrip", "model_name": "deepseek-chat"},
        })
        self.assertEqual(code, 0, msg)
        self.assertTrue(data["saved"])

        code, data, _, _ = self.invoke("config.get", {})
        self.assertEqual(data["config"]["api_key"], "sk-e2e-.roundtrip")
        self.assertEqual(data["config"]["model_name"], "deepseek-chat")

        # 持久化到用户配置文件（集中存储 ADR_005：<base>/config/llm_config.json）
        self.assertTrue((self.home / "config" / "llm_config.json").exists())

        # 卫生回滚：清空密钥，避免影响后续用例/重跑
        self.invoke("config.save", {"config": {"api_key": ""}})

    # ------------------------------------------------------------------
    # 旅程五：跨进程持久化——独立进程（模拟应用重启）读回书库/批注/配置
    # ------------------------------------------------------------------
    def test_05_cross_process_persistence_after_restart(self):
        code, data, msg, _ = self.invoke("annotation.save", {
            "book_id": self.book_id,
            "section_id": self.first_section_id,
            "style": "margin_note",
            "color": "#007AFF",
            "note_text": "重启留存探针批注",
            "anchor": {"paragraph_id": "p1", "start": 0, "end": 3},
        })
        self.assertEqual(code, 0, msg)
        probe_id = data["annotation_id"]

        env = dict(os.environ)
        env["AI_READER_HOME"] = str(self.home)
        env["HOME"] = str(self.home)
        probe_json = self.home / "restart_probe.json"
        proc = subprocess.run(
            [sys.executable, "-c", RESTART_PROBE_SNIPPET, str(LIB_PATH), str(self.book_id), str(probe_json)],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, f"重启探针进程失败: {proc.stderr[-2000:]}")
        snapshot = json.loads(probe_json.read_text(encoding="utf-8"))

        book = next(b for b in snapshot["books"] if b["id"] == self.book_id)
        self.assertEqual(book["sections_count"], 2, "重启后书籍与章节数应留存")

        probe = next(
            (a for a in snapshot["annotations"] if a["id"] == probe_id), None)
        self.assertIsNotNone(probe, "重启后批注应留存")
        self.assertEqual(probe["note_text"], "重启留存探针批注")

        self.assertEqual(
            snapshot["config"]["endpoint"], "https://api.deepseek.com/v1",
            "重启后配置应可加载",
        )


if __name__ == "__main__":
    unittest.main()
