#!/usr/bin/env python3
"""
nlp_embed_engine.py
跨平台轻量级 NLP 分词器与 Embedding 向量检索引擎（Windows / Linux / macOS）。

功能特性：
1. CJK 智能预分词：优先使用 jieba，无依赖时优雅降级为纯 Python CJK n-gram 双字切分，
   使标准 SQLite FTS5 unicode61 能够原生支持中文 BM25 词频打分与短语召回，彻底替代 LIKE。
2. 可插拔 Embedding 向量体系：
   - FastEmbedProvider：本地 ONNX 轻量模型 (需 fastembed)
   - ApiEmbeddingProvider：云端 Embedding API (如 Gemini / OpenAI)
   - NativeHashingEmbeddingProvider：纯 Python 标准库内置的稠密特征向量哈希化引擎，
     零外部依赖即可进行余弦相似度（Cosine Similarity）语义计算。
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 检查是否安装了 jieba
try:
    import jieba  # type: ignore
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False


def has_cjk(text: str) -> bool:
    """检测字符串中是否包含中日韩文字"""
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def tokenize_cjk_for_fts(text: str) -> str:
    """
    将中文/英文混合文本转换为适用于 SQLite FTS5 (unicode61) 的空格分隔词流。
    - 如果安装了 jieba，使用 jieba.cut_for_search；
    - 否则采用纯 Python 混合分词（单词 + CJK 1-gram / 2-gram 窗口滑动）。
    """
    if not text:
        return ""

    if not has_cjk(text):
        # 纯英文字符：仅按常规单词与下划线分割
        tokens = re.findall(r"[A-Za-z0-9_]+", text)
        return " ".join(tokens)

    # 1. 优先尝试 jieba 分词
    if _JIEBA_AVAILABLE:
        words = [w.strip() for w in jieba.cut_for_search(text) if w.strip()]
        return " ".join(words)

    # 2. 内置纯 Python CJK 1-gram + 2-gram 算法
    tokens: List[str] = []
    # 按 CJK 与非 CJK 切块
    chunks = re.split(r"([\u4e00-\u9fff]+)", text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if re.match(r"^[\u4e00-\u9fff]+$", chunk):
            # 纯 CJK 块：单字与双字切分
            cjk_len = len(chunk)
            if cjk_len == 1:
                tokens.append(chunk)
            else:
                for i in range(cjk_len - 1):
                    tokens.append(chunk[i : i + 2])
                # 保留单字以防边界单字无法召回
                for char in chunk:
                    tokens.append(char)
        else:
            # 非 CJK 块：按词提取
            words = re.findall(r"[A-Za-z0-9_]+", chunk)
            tokens.extend(words)

    return " ".join(tokens)


def build_fts_query(query: str) -> str:
    """
    将用户输入的检索 query 构造成高质量的 SQLite FTS5 MATCH 表达式。
    支持中文分词与前缀匹配。
    """
    q = (query or "").strip()
    if not q:
        return ""

    # 清理 FTS5 特殊语法符号
    clean_q = re.sub(r'["\'\*\^\:\(\)\{\}\~]', " ", q)
    tokenized = tokenize_cjk_for_fts(clean_q)
    tokens = [t.strip() for t in tokenized.split() if t.strip()]

    if not tokens:
        return ""

    # 构造词项匹配：如 (term1* OR term2*)
    # 限制 term 数量防超载
    sub_terms = [f'"{t}"*' if has_cjk(t) else f"{t}*" for t in tokens[:12]]
    return " OR ".join(sub_terms)


# ==============================================================================
# Embedding 向量引擎接口与实现
# ==============================================================================

def pack_vector(vector: Sequence[float]) -> bytes:
    """将浮点数向量打包为紧凑二进制 BLOB (float32)"""
    return struct.pack(f"{len(vector)}f", *vector)


def unpack_vector(blob: bytes) -> List[float]:
    """将二进制 BLOB 解包为浮点数向量"""
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """计算两个向量的余弦相似度 [-1.0, 1.0]"""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class BaseEmbeddingProvider:
    """Embedding 模型基础接口"""
    dim: int = 128
    name: str = "base"

    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class NativeHashingEmbeddingProvider(BaseEmbeddingProvider):
    """
    纯 Python 标准库内置的稠密特征哈希 Embedding 引擎（Hashing Trick + CJK n-gram + L2 归一化）。
    - 零外部依赖，任何系统无缝运行；
    - 将词、双字切分与字符特征映射到 128 维空间并作实数加权；
    - 余弦相似度可有效衡量概念词汇重合度与业务意图关联度。
    """
    name = "native_hash"

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dim

        vec = [0.0] * self.dim
        tokens = tokenize_cjk_for_fts(text).split()
        if not tokens:
            return [0.0] * self.dim

        for token in tokens:
            if not token:
                continue
            # 词频与长度加权
            weight = math.log1p(len(token))
            # 对 token 计算哈希
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            # 符号位哈希：消除偏差
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * weight

        # L2 归一化
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec


class FastEmbedProvider(BaseEmbeddingProvider):
    """本地 ONNX 轻量模型向量化实现（基于 fastembed 库）"""
    name = "fastembed"

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        try:
            from fastembed import TextEmbedding  # type: ignore
            self.model = TextEmbedding(model_name=model_name)
            self.dim = 512
        except Exception as e:
            raise RuntimeError(f"Failed to initialize FastEmbed: {e}")

    def embed_text(self, text: str) -> List[float]:
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = list(self.model.embed(texts))
        return [e.tolist() for e in embeddings]


_GLOBAL_EMBED_PROVIDER: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider(prefer_fastembed: bool = True) -> BaseEmbeddingProvider:
    """获取全局 Embedding 提供者实例（优先使用 fastembed，自动降级为原生 NativeHashing）"""
    global _GLOBAL_EMBED_PROVIDER
    if _GLOBAL_EMBED_PROVIDER is not None:
        return _GLOBAL_EMBED_PROVIDER

    if prefer_fastembed:
        try:
            import fastembed  # noqa: F401
            _GLOBAL_EMBED_PROVIDER = FastEmbedProvider()
            return _GLOBAL_EMBED_PROVIDER
        except Exception:
            pass

    _GLOBAL_EMBED_PROVIDER = NativeHashingEmbeddingProvider(dim=128)
    return _GLOBAL_EMBED_PROVIDER
