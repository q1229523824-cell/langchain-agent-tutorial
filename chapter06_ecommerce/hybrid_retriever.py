"""电商知识库的 BM25 + 本地哈希向量 + 轻量重排。

默认编码器完全离线、零下载，保证作品可以直接运行和测试。它不是神经网络
Embedding，因此文档和简历必须如实称为“本地哈希向量”。生产环境可通过
``VectorEncoder`` 协议替换成真实 Embedding 服务，而不用修改检索编排。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from langchain_core.documents import Document

from chapter04_rag.project_knowledge import (
    BM25Index,
    load_project_documents,
    split_project_documents,
    tokenize_for_bm25,
)


class VectorEncoder(Protocol):
    """可替换的向量编码接口。"""

    def encode(self, text: str) -> list[float]: ...


class LocalHashVectorEncoder:
    """将中英文 token 哈希到固定维度，并进行 L2 归一化。"""

    SYNONYMS = {
        "退钱": "退款 售后",
        "不要了": "退货 七天无理由",
        "什么时候到": "物流 配送 时效",
        "快递": "物流 配送",
        "坏了": "质量问题 售后 换货",
        "发票": "电子发票 开票",
        "耳麦": "耳机 数码音频",
    }

    def __init__(self, dimensions: int = 384):
        if dimensions < 64:
            raise ValueError("dimensions 不能小于 64。")
        self.dimensions = dimensions

    def _normalize_text(self, text: str) -> str:
        normalized = text.lower()
        for source, target in self.SYNONYMS.items():
            if source in normalized:
                normalized += f" {target}"
        return normalized

    def encode(self, text: str) -> list[float]:
        tokens = tokenize_for_bm25(self._normalize_text(text))
        vector = [0.0] * self.dimensions
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1.0 if number & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


@dataclass(frozen=True)
class HybridRetrievalHit:
    document: Document
    bm25_score: float
    vector_score: float
    fusion_score: float
    rerank_score: float

    @property
    def citation(self) -> str:
        metadata = self.document.metadata
        return f"{metadata['source']}:L{metadata['start_line']}-L{metadata['end_line']}"

    def as_payload(self) -> dict[str, object]:
        return {
            "citation": self.citation,
            "content": self.document.page_content.strip(),
            "bm25_score": round(self.bm25_score, 4),
            "vector_score": round(self.vector_score, 4),
            "fusion_score": round(self.fusion_score, 4),
            "rerank_score": round(self.rerank_score, 4),
        }


class HybridCommerceRetriever:
    """并行召回、RRF 融合和轻量规则重排。"""

    def __init__(self, chunks: list[Document], encoder: VectorEncoder | None = None):
        self.chunks = chunks
        self.bm25 = BM25Index(chunks)
        self.encoder = encoder or LocalHashVectorEncoder()
        self.vectors = [self.encoder.encode(chunk.page_content) for chunk in chunks]

    @classmethod
    def from_directory(cls, knowledge_root: Path) -> "HybridCommerceRetriever":
        documents = load_project_documents(knowledge_root)
        chunks = split_project_documents(documents, chunk_size=700, chunk_overlap=100)
        return cls(chunks)

    def search(self, query: str, *, top_k: int = 3) -> list[HybridRetrievalHit]:
        if not 1 <= top_k <= 5:
            raise ValueError("top_k 必须位于 1 到 5 之间。")
        query = query.strip()
        if not query or not self.chunks:
            return []

        candidate_size = min(5, len(self.chunks))
        bm25_hits = self.bm25.search(query, top_k=candidate_size)
        bm25_by_id = {id(hit.document): hit.score for hit in bm25_hits}
        bm25_rank = {id(hit.document): rank for rank, hit in enumerate(bm25_hits, start=1)}

        query_vector = self.encoder.encode(query)
        vector_ranked = sorted(
            (
                (_cosine(query_vector, vector), document)
                for document, vector in zip(self.chunks, self.vectors, strict=True)
            ),
            key=lambda item: (-item[0], str(item[1].metadata.get("source", ""))),
        )[:candidate_size]
        vector_by_id = {id(document): score for score, document in vector_ranked}
        vector_rank = {
            id(document): rank for rank, (_, document) in enumerate(vector_ranked, start=1)
        }

        candidate_ids = set(bm25_by_id) | set(vector_by_id)
        query_terms = set(tokenize_for_bm25(query))
        results: list[HybridRetrievalHit] = []
        for document in self.chunks:
            document_id = id(document)
            if document_id not in candidate_ids:
                continue
            fusion = 0.0
            if document_id in bm25_rank:
                fusion += 1 / (60 + bm25_rank[document_id])
            if document_id in vector_rank:
                fusion += 1 / (60 + vector_rank[document_id])

            document_terms = set(tokenize_for_bm25(document.page_content))
            lexical_overlap = len(query_terms & document_terms) / max(1, len(query_terms))
            # 重排阶段兼顾融合排名、精确词覆盖和向量相似度。
            rerank = fusion * 10 + lexical_overlap * 0.6 + max(
                0.0, vector_by_id.get(document_id, 0.0)
            ) * 0.2
            results.append(
                HybridRetrievalHit(
                    document=document,
                    bm25_score=bm25_by_id.get(document_id, 0.0),
                    vector_score=vector_by_id.get(document_id, 0.0),
                    fusion_score=fusion,
                    rerank_score=rerank,
                )
            )

        results.sort(key=lambda hit: (-hit.rerank_score, hit.citation))
        return results[:top_k]

    def format_results(self, query: str, *, top_k: int = 3) -> str:
        hits = self.search(query, top_k=top_k)
        if not hits:
            return f"没有找到与“{query}”相关的电商政策。"
        return "\n\n".join(
            f"[来源 {index}] {hit.citation}  重排分={hit.rerank_score:.3f}\n"
            f"{hit.document.page_content.strip()}"
            for index, hit in enumerate(hits, start=1)
        )
