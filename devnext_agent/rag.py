"""Hybrid RAG engine (Gemini Embeddings + BM25) for ET TechGig DevNext '26."""

from __future__ import annotations

import contextvars
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
from google import genai

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"
CACHE_PATH = BASE_DIR / ".rag_cache.json"

# Context variable holding a request-scoped mutable list of retrieved chunks
LAST_RETRIEVED_SOURCES: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "LAST_RETRIEVED_SOURCES", default=None
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "please", "tell", "that", "the", "their", "there", "this", "to",
    "was", "what", "when", "where", "which", "who", "why", "will", "with",
    "you", "your", "about",
}


@dataclass
class KBChunk:
    chunk_id: str
    source_file: str
    section: str
    content: str


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\.\-\+@']*", text.lower())
    return [t.strip(".-'") for t in tokens if len(t.strip(".-'")) > 1 and t not in STOPWORDS]


class DevNextRAGEngine:
    """Indexes Markdown/Text event documents and serves hybrid vector + lexical search."""

    def __init__(self, kb_dir: Path = KB_DIR) -> None:
        self.kb_dir = kb_dir
        self.chunks: list[KBChunk] = []
        self.doc_tokens: list[list[str]] = []
        self.doc_freqs: dict[str, int] = {}
        self.avg_dl: float = 1.0
        self.embeddings: np.ndarray | None = None
        self.embedding_model_used: str | None = None
        self._corpus_hash: str = ""
        self.reload()

    def reload(self) -> None:
        """Loads and chunks all .md and .txt files in knowledge_base/."""
        self.chunks = self._load_chunks()
        self._build_bm25_index()
        self._corpus_hash = self._compute_corpus_hash()
        self.embeddings = None
        self.embedding_model_used = None
        self._try_load_or_build_embeddings()

    def _load_chunks(self) -> list[KBChunk]:
        chunks: list[KBChunk] = []
        if not self.kb_dir.exists():
            return chunks

        files = sorted(
            [p for p in self.kb_dir.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt"}]
        )
        idx = 1
        for file_path in files:
            raw_text = file_path.read_text(encoding="utf-8").strip()
            if not raw_text:
                continue

            # Split Markdown by ## headings while preserving section titles
            sections = re.split(r"(?m)^##\s+", raw_text)
            doc_title = file_path.stem.replace("_", " ").title()

            for sec_i, block in enumerate(sections):
                block = block.strip()
                if not block:
                    continue
                if sec_i == 0 and block.startswith("# "):
                    lines = block.splitlines()
                    doc_title = lines[0].lstrip("# ").strip()
                    remainder = "\n".join(lines[1:]).strip()
                    if not remainder:
                        continue
                    section_title = f"{doc_title} — Introduction"
                    body = remainder
                else:
                    lines = block.splitlines()
                    section_title = lines[0].strip()
                    body = "\n".join(lines[1:]).strip()

                if not body:
                    continue

                # Sub-chunk very large sections (>2200 chars) by paragraph groups
                if len(body) <= 2200:
                    chunks.append(
                        KBChunk(
                            chunk_id=f"chunk_{idx:02d}",
                            source_file=file_path.name,
                            section=section_title,
                            content=f"## {section_title}\n{body}",
                        )
                    )
                    idx += 1
                else:
                    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                    buffer: list[str] = []
                    buf_len = 0
                    part_num = 1
                    for para in paragraphs:
                        if buffer and buf_len + len(para) > 1600:
                            chunks.append(
                                KBChunk(
                                    chunk_id=f"chunk_{idx:02d}",
                                    source_file=file_path.name,
                                    section=f"{section_title} (Part {part_num})",
                                    content=f"## {section_title} (Part {part_num})\n" + "\n\n".join(buffer),
                                )
                            )
                            idx += 1
                            part_num += 1
                            buffer = [para]
                            buf_len = len(para)
                        else:
                            buffer.append(para)
                            buf_len += len(para)
                    if buffer:
                        label = f"{section_title} (Part {part_num})" if part_num > 1 else section_title
                        chunks.append(
                            KBChunk(
                                chunk_id=f"chunk_{idx:02d}",
                                source_file=file_path.name,
                                section=label,
                                content=f"## {label}\n" + "\n\n".join(buffer),
                            )
                        )
                        idx += 1

        return chunks

    def _build_bm25_index(self) -> None:
        self.doc_tokens = []
        self.doc_freqs = {}
        total_len = 0
        for chunk in self.chunks:
            tokens = _tokenize(f"{chunk.section} {chunk.content}")
            self.doc_tokens.append(tokens)
            total_len += len(tokens)
            for tok in set(tokens):
                self.doc_freqs[tok] = self.doc_freqs.get(tok, 0) + 1
        self.avg_dl = (total_len / len(self.chunks)) if self.chunks else 1.0

    def _compute_corpus_hash(self) -> str:
        embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        payload = json.dumps(
            {
                "model": embedding_model,
                "chunks": [asdict(c) for c in self.chunks],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _has_api_credentials(self) -> bool:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        if key and key != "your_gemini_api_key_here":
            return True
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"true", "1"}:
            return True
        return False

    def _get_genai_client(self) -> genai.Client | None:
        if not self._has_api_credentials():
            return None
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"true", "1"}:
            return genai.Client(vertexai=True)
        return genai.Client(api_key=api_key)

    def _try_load_or_build_embeddings(self) -> bool:
        """Loads cached embeddings or computes fresh Gemini embeddings when credentials exist."""
        if not self.chunks:
            return False

        embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

        # 1. Check disk cache first
        if CACHE_PATH.exists():
            try:
                cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                if cached.get("corpus_hash") == self._corpus_hash:
                    vecs = np.array(cached["embeddings"], dtype=np.float32)
                    if vecs.shape[0] == len(self.chunks):
                        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
                        self.embeddings = vecs / norms
                        self.embedding_model_used = embedding_model
                        return True
            except Exception:
                pass

        # 2. Compute via Gemini Embeddings API if credentials are set
        client = self._get_genai_client()
        if client is None:
            return False

        try:
            texts = [c.content for c in self.chunks]
            resp = client.models.embed_content(
                model=embedding_model,
                contents=texts,
            )
            raw_vecs = [emb.values for emb in resp.embeddings]
            vecs = np.array(raw_vecs, dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
            self.embeddings = vecs / norms
            self.embedding_model_used = embedding_model

            CACHE_PATH.write_text(
                json.dumps(
                    {
                        "corpus_hash": self._corpus_hash,
                        "model": embedding_model,
                        "embeddings": raw_vecs,
                    }
                ),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False

    def _bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        n_docs = len(self.chunks)
        if n_docs == 0:
            return np.array([], dtype=np.float32)

        q_tokens = _tokenize(query)
        scores = np.zeros(n_docs, dtype=np.float32)
        q_lower = query.lower().strip()

        for i, doc_toks in enumerate(self.doc_tokens):
            dl = len(doc_toks) or 1
            tf_map: dict[str, int] = {}
            for t in doc_toks:
                tf_map[t] = tf_map.get(t, 0) + 1

            score = 0.0
            for qt in q_tokens:
                tf = tf_map.get(qt, 0)
                if tf == 0:
                    # Partial prefix/substring match for names like "ashutosh", "sarvam", "refund"
                    partial_hits = sum(1 for dt in tf_map if (qt in dt or dt in qt) and len(qt) >= 4)
                    if partial_hits:
                        score += 0.65 * partial_hits
                    continue
                df = self.doc_freqs.get(qt, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1.0 - b + b * (dl / self.avg_dl))
                score += idf * ((tf * (k1 + 1.0)) / denom)

            if len(q_lower) >= 5 and q_lower in self.chunks[i].content.lower():
                score += 2.0

            scores[i] = score

        return scores

    def search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Performs hybrid dense + BM25 retrieval over the DevNext '26 knowledge base."""
        if not self.chunks:
            return {"mode": "empty", "results": []}

        # Ensure embeddings are built once API credentials become available
        if self.embeddings is None and self._has_api_credentials():
            self._try_load_or_build_embeddings()

        bm25 = self._bm25_scores(query)
        bm25_norm = bm25 / (bm25.max() + 1e-8) if bm25.max() > 0 else bm25

        dense_scores: np.ndarray | None = None
        client = self._get_genai_client()
        if self.embeddings is not None and client is not None:
            try:
                embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
                q_resp = client.models.embed_content(
                    model=embedding_model,
                    contents=query,
                )
                q_vec = np.array(q_resp.embeddings[0].values, dtype=np.float32)
                q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-10)
                cos_sim = self.embeddings @ q_vec
                # Shift cosine [-1, 1] into [0, 1]
                dense_scores = np.clip((cos_sim + 1.0) / 2.0, 0.0, 1.0)
            except Exception:
                dense_scores = None

        if dense_scores is not None:
            combined = 0.70 * dense_scores + 0.30 * bm25_norm
            mode = f"hybrid ({self.embedding_model_used} + BM25)"
        else:
            combined = bm25_norm
            mode = "lexical (BM25)"

        ranked_indices = np.argsort(combined)[::-1][: max(1, min(top_k, len(self.chunks)))]
        results: list[dict[str, Any]] = []
        for idx in ranked_indices:
            chunk = self.chunks[int(idx)]
            score_val = float(combined[int(idx)])
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "section": chunk.section,
                    "source_file": chunk.source_file,
                    "score": round(score_val, 4),
                    "content": chunk.content,
                }
            )

        # Append in-place to request-scoped list so threadpool/subtask tool calls propagate to parent
        bucket = LAST_RETRIEVED_SOURCES.get()
        if bucket is not None:
            seen_ids = {item["chunk_id"] for item in bucket}
            for item in results:
                if item["chunk_id"] not in seen_ids:
                    bucket.append(
                        {
                            "chunk_id": item["chunk_id"],
                            "section": item["section"],
                            "source_file": item["source_file"],
                            "score": item["score"],
                            "mode": mode,
                            "snippet": item["content"][:260].replace("\n", " ").strip() + "...",
                        }
                    )
                    seen_ids.add(item["chunk_id"])

        return {
            "event": "ET TechGig DevNext '26 (Hyderabad — November 21, 2026)",
            "official_url": "https://techgig.com/devnext",
            "retrieval_mode": mode,
            "matched_sections": results,
        }


# Singleton RAG engine instance
rag_engine = DevNextRAGEngine()


def search_devnext_knowledge(query: str) -> dict[str, Any]:
    """Searches the official ET TechGig DevNext 2026 event knowledge base using RAG.

    Always call this tool to retrieve verified facts about ET TechGig DevNext '26
    including event dates, timings, Hyderabad location, organizer heritage, conference tracks,
    the 16 speakers and their companies, The CTO Lounge, target audience / who should attend,
    registration, ticket refund policy, FAQs, and sponsorship/speakership/escalation contacts.

    Args:
        query: A focused search query describing the DevNext 2026 information needed.

    Returns:
        A dictionary containing the top matching knowledge base chunks and metadata.
    """
    return rag_engine.search(query=query, top_k=5)

