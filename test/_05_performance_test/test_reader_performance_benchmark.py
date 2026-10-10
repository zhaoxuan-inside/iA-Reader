#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/_05_performance_test/test_reader_performance_benchmark.py
AI Reader 性能基准与高负载压力测试 (Performance Benchmark & SLA Verification)
严格按照 quality_gates.md 与 PRD 指标要求：
  - 10 万字文档冷启动解构时延 < 1500ms
  - 离线 NLP 与 PMI 概念拓扑生成耗时 < 200ms
  - 认知伴读响应时延 P99 < 800ms (离线启发卡片 < 10ms)
  - SQLite WAL 高并发并发读写零锁等待异常
"""

import os
import sys
import time
import json
import unittest
import threading
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

PERF_DB = WORKSPACE_ROOT / "test_perf_suite.db"
os.environ["AI_READER_DB_PATH"] = str(PERF_DB)

from backend.reader_engine import (
    get_engine,
    ai_reader_invoke,
    calculate_tfidf,
    calculate_textrank,
    build_co_occurrence,
    tokenize,
)


class TestReaderPerformanceBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PERF_DB.exists():
            PERF_DB.unlink()
        cls.engine = get_engine()

        # 生成 5 万字的高仿真长篇技术论著文档
        cls.large_doc = WORKSPACE_ROOT / "perf_large_document.md"
        paragraphs = []
        for i in range(1, 51):
            paragraphs.append(f"# 第 {i} 章 分布式系统架构设计模式-{i}\n")
            for j in range(1, 11):
                paragraphs.append(
                    f"在第 {i} 章第 {j} 节中，我们探讨核心并发控制与快照隔离协议。"
                    "预写式日志（WAL）与多版本并发控制（MVCC）在分布式数据库设计中相辅相成。"
                    "通过追加写与时间戳定序，读取者绝不阻塞写入者，写入者也绝不阻塞读取者。"
                    "离线三级 NLP 概念图谱计算引擎在此处对段落进行精准切片与 PMI 拓扑分析。\n"
                )
        cls.large_doc.write_text("\n".join(paragraphs), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        if PERF_DB.exists():
            PERF_DB.unlink()
        if cls.large_doc.exists():
            cls.large_doc.unlink()

    def test_01_large_doc_parse_latency_benchmark(self):
        """[SLA-1] 5~10 万字长篇文档冷启动解构耗时必须 < 1500ms"""
        start = time.time()
        res_raw = ai_reader_invoke("doc.parse", json.dumps({"file_path": str(self.large_doc)}))
        duration_ms = (time.time() - start) * 1000.0

        res = json.loads(res_raw)
        self.assertEqual(res["code"], 0)
        self.assertLess(duration_ms, 1500.0, f"文档解析耗时超标: {duration_ms:.2f}ms (上限 1500ms)")
        print(f"\n[BENCHMARK] doc.parse for 50 chapters: {duration_ms:.2f}ms (SLA: < 1500ms)")

    def test_02_pmi_topology_and_nlp_benchmark(self):
        """[SLA-2] 离线三级 NLP 关键词与 PMI 共现拓扑图计算耗时必须 < 200ms"""
        # 1. 关键词抽取耗时
        start = time.time()
        res_kw_raw = ai_reader_invoke("nlp.keyword_extract", json.dumps({"book_id": 1, "top_k": 30}))
        kw_ms = (time.time() - start) * 1000.0
        res_kw = json.loads(res_kw_raw)
        self.assertEqual(res_kw["code"], 0)
        self.assertLess(kw_ms, 100.0, f"关键词抽取耗时: {kw_ms:.2f}ms")

        # 2. PMI 拓扑生成耗时
        start = time.time()
        res_graph_raw = ai_reader_invoke("graph.build", json.dumps({"book_id": 1}))
        graph_ms = (time.time() - start) * 1000.0
        res_graph = json.loads(res_graph_raw)
        self.assertEqual(res_graph["code"], 0)
        self.assertLess(graph_ms, 200.0, f"PMI 拓扑构建耗时: {graph_ms:.2f}ms (上限 200ms)")
        print(f"[BENCHMARK] nlp_keywords: {kw_ms:.2f}ms, graph_build: {graph_ms:.2f}ms (SLA: < 200ms)")

    def test_03_ai_companion_p99_latency_benchmark(self):
        """[SLA-3] 认知伴读连续请求响应耗时 P99 必须 < 800ms"""
        latencies = []
        for i in range(20):
            start = time.time()
            res_raw = ai_reader_invoke("ai.companion_ask", json.dumps({
                "book_id": 1,
                "template_type": "logic",
                "selected_text": f"第 {i} 轮并发读写吞吐量测试样本段落",
                "prompt": ""
            }))
            latencies.append((time.time() - start) * 1000.0)
            res = json.loads(res_raw)
            self.assertEqual(res["code"], 0)

        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p90 = latencies[int(len(latencies) * 0.90)]
        p99 = latencies[-1]

        self.assertLess(p99, 800.0, f"伴读 P99 延迟超标: {p99:.2f}ms (上限 800ms)")
        print(f"[BENCHMARK] companion_ask 20 runs -> P50: {p50:.2f}ms, P90: {p90:.2f}ms, P99: {p99:.2f}ms")

    def test_04_sqlite_wal_concurrent_stress_benchmark(self):
        """[SLA-4] SQLite WAL 多线程并发原子写入压力测试，零死锁与零锁超时"""
        errors = []
        thread_count = 10
        ops_per_thread = 10

        def worker(tid):
            for i in range(ops_per_thread):
                try:
                    res_raw = ai_reader_invoke("annotation.save", json.dumps({
                        "book_id": 1,
                        "section_id": 1,
                        "note_text": f"Thread {tid} Note {i}",
                        "color": "#007AFF"
                    }))
                    res = json.loads(res_raw)
                    if res["code"] != 0:
                        errors.append(f"Thread {tid} error: {res['message']}")
                except Exception as e:
                    errors.append(f"Thread {tid} exception: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = (time.time() - start) * 1000.0

        self.assertEqual(len(errors), 0, f"并发读写发生冲突错误: {errors}")
        total_ops = thread_count * ops_per_thread
        qps = total_ops / (total_time / 1000.0)
        print(f"[BENCHMARK] Concurrent SQLite writes: {total_ops} ops in {total_time:.2f}ms ({qps:.1f} QPS)")


if __name__ == "__main__":
    unittest.main()
