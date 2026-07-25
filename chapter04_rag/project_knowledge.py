"""项目知识库：把本地文档切块，并使用轻量 BM25 检索相关上下文。

Day 5 暂时不引入 Embedding 模型和向量数据库，目的是先把 RAG 的主链路讲清楚：

    文档加载 -> 文档切块 -> 建立索引 -> 查询 Top-K -> 返回来源 -> 模型生成答案

BM25 属于关键词相关性算法，因此它不等同于语义向量检索。后续可以在保持
``ProjectKnowledgeBase.search`` 接口不变的情况下，把内部实现替换为向量数据库。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# RAG 只索引适合发送给模型的文本文件。隐藏文件、密钥和本地个人笔记不进入知识库。
ALLOWED_KNOWLEDGE_SUFFIXES = {".md", ".py", ".txt", ".toml", ".yaml", ".yml"}
EXCLUDED_DIRECTORIES = {
    ".agent_data",
    ".git",
    ".idea",
    ".tools",
    ".venv",
    "__pycache__",
    "interview_note",
    "tests",
}
EXCLUDED_FILENAMES = {"AGENTS.md"}

# 英文按单词/标识符切分；连续中文同时生成单字和双字词，提高短中文查询的召回率。
ENGLISH_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
CHINESE_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class RetrievalHit:
    """一条检索结果，保留文本、分数和可引用的来源元数据。"""

    document: Document
    score: float

    @property
    def source(self) -> str:
        return str(self.document.metadata["source"])

    @property
    def start_line(self) -> int:
        return int(self.document.metadata["start_line"])

    @property
    def end_line(self) -> int:
        return int(self.document.metadata["end_line"])

    @property
    def citation(self) -> str:
        return f"{self.source}:L{self.start_line}-L{self.end_line}"


def tokenize_for_bm25(text: str) -> list[str]:
    """把中英文文本转换为 BM25 token。

    这里故意采用可读、零额外模型依赖的分词策略：

    - 英文、数字、Python 标识符转成小写 token；
    - 中文连续文本生成单字和相邻双字 token；
    - 不把原文发送到任何外部服务。
    """

    lowered = text.lower()
    tokens = ENGLISH_TOKEN_PATTERN.findall(lowered)
    for sequence in CHINESE_SEQUENCE_PATTERN.findall(lowered):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tokens


def _is_allowed_source(path: Path, project_root: Path) -> bool:
    """判断文件是否可以进入知识库，避免索引密钥、隐藏目录和个人笔记。"""

    try:
        relative = path.relative_to(project_root)
    except ValueError:
        return False

    if path.name in EXCLUDED_FILENAMES or path.name.startswith("."):
        return False
    if any(part.startswith(".") or part in EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
        return False
    return path.is_file() and path.suffix.lower() in ALLOWED_KNOWLEDGE_SUFFIXES


def load_project_documents(project_root: Path) -> list[Document]:
    """读取允许的项目文件，并把来源路径放入 Document.metadata。"""

    project_root = project_root.resolve()
    documents: list[Document] = []
    for path in sorted(project_root.rglob("*")):
        if not _is_allowed_source(path, project_root):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not content.strip():
            continue
        documents.append(
            Document(
                page_content=content,
                metadata={"source": path.relative_to(project_root).as_posix()},
            )
        )
    return documents


def split_project_documents(
    documents: Iterable[Document],
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[Document]:
    """把大文件切成可检索的知识块，并补充原文件行号。

    overlap 让相邻块共享少量文本，避免答案所需的一句话刚好被切块边界拆开。
    ``add_start_index`` 保存块在原文中的字符位置，再由换行符数量换算成行号。
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0。")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size。")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    chunks: list[Document] = []
    for document in documents:
        source_text = document.page_content
        for chunk in splitter.split_documents([document]):
            start_index = int(chunk.metadata.get("start_index", 0))
            start_line = source_text.count("\n", 0, start_index) + 1
            end_index = start_index + len(chunk.page_content)
            end_line = source_text.count("\n", 0, end_index) + 1
            chunk.metadata.update({"start_line": start_line, "end_line": end_line})
            chunks.append(chunk)
    return chunks


class BM25Index:
    """一个适合教学和小型本地知识库的 BM25 实现。"""

    def __init__(self, documents: list[Document], *, k1: float = 1.5, b: float = 0.75):
        if k1 <= 0:
            raise ValueError("k1 必须大于 0。")
        if not 0 <= b <= 1:
            raise ValueError("b 必须位于 0 到 1 之间。")

        self.documents = documents
        self.k1 = k1
        self.b = b
        self._term_frequencies = [Counter(tokenize_for_bm25(doc.page_content)) for doc in documents]
        self._document_lengths = [sum(frequencies.values()) for frequencies in self._term_frequencies]
        self._average_length = (
            sum(self._document_lengths) / len(self._document_lengths)
            if self._document_lengths
            else 0.0
        )

        # document_frequency 表示某个词出现在多少个知识块中，用于降低常见词权重。
        self._document_frequency: Counter[str] = Counter()
        for frequencies in self._term_frequencies:
            self._document_frequency.update(frequencies.keys())

    def _idf(self, term: str) -> float:
        document_count = len(self.documents)
        frequency = self._document_frequency.get(term, 0)
        return math.log(1 + (document_count - frequency + 0.5) / (frequency + 0.5))

    def search(self, query: str, *, top_k: int = 4) -> list[RetrievalHit]:
        """返回与查询最相关的 Top-K 知识块。"""

        if not 1 <= top_k <= 5:
            raise ValueError("top_k 必须位于 1 到 5 之间。")
        query_tokens = tokenize_for_bm25(query.strip())
        if not query_tokens or not self.documents:
            return []

        query_terms = set(query_tokens)
        scored: list[RetrievalHit] = []
        for index, frequencies in enumerate(self._term_frequencies):
            document_length = self._document_lengths[index]
            score = 0.0
            for term in query_terms:
                term_frequency = frequencies.get(term, 0)
                if not term_frequency:
                    continue
                length_ratio = (
                    document_length / self._average_length if self._average_length else 0.0
                )
                denominator = term_frequency + self.k1 * (1 - self.b + self.b * length_ratio)
                score += self._idf(term) * (term_frequency * (self.k1 + 1)) / denominator
            if score > 0:
                scored.append(RetrievalHit(document=self.documents[index], score=score))

        scored.sort(key=lambda hit: (-hit.score, hit.source, hit.start_line))
        return scored[:top_k]


class ProjectKnowledgeBase:
    """封装项目文档加载、切块、索引和格式化输出。"""

    def __init__(self, chunks: list[Document]):
        self.chunks = chunks
        self.index = BM25Index(chunks)

    @classmethod
    def from_project(
        cls,
        project_root: Path,
        *,
        chunk_size: int = 900,
        chunk_overlap: int = 150,
    ) -> "ProjectKnowledgeBase":
        documents = load_project_documents(project_root)
        chunks = split_project_documents(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return cls(chunks)

    def search(self, query: str, *, top_k: int = 4) -> list[RetrievalHit]:
        return self.index.search(query, top_k=top_k)

    def format_search_results(self, query: str, *, top_k: int = 4) -> str:
        """返回适合放进 ToolMessage 的带来源文本。"""

        query = query.strip()
        if not query:
            return "检索问题不能为空。"
        try:
            hits = self.search(query, top_k=top_k)
        except ValueError as error:
            return f"检索失败：{error}"
        if not hits:
            return f"没有找到与“{query}”相关的项目知识。"

        sections: list[str] = []
        for number, hit in enumerate(hits, start=1):
            sections.append(
                f"[来源 {number}] {hit.citation}  相关度={hit.score:.3f}\n"
                f"{hit.document.page_content.strip()}"
            )
        return "\n\n".join(sections)


@lru_cache(maxsize=4)
def get_project_knowledge_base(project_root: str) -> ProjectKnowledgeBase:
    """每个 Python 进程只构建一次索引，避免每轮对话重复扫描项目。"""

    return ProjectKnowledgeBase.from_project(Path(project_root))
