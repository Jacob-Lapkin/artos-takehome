"""RetrievalService: hybrid retrieval, filters, fusion, and trimming.

Loads FAISS + Gemini embeddings via LangChain and a local BM25 model to
perform hybrid retrieval. Applies heading-based filters per target ICF
section, fuses sparse and dense scores, and returns top snippets.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from app.config import Config
from app.utils.bm25 import bm25_top_k, load_bm25
from app.utils.io_utils import read_json
from app.utils.langchain_processing import count_tokens


SECTION_ALLOWED_HEADINGS = {
    "Purpose": ["objectives", "primary objective", "secondary objectives", "background", "rationale"],
    "Procedures": [
        "study design",
        "study procedures",
        "treatment plan",
        "schedule of assessments",
        "sample size",
        "enrollment",
        "duration",
        "follow-up",
    ],
    "Risks": ["risks", "potential risks", "safety", "adverse events", "warnings"],
    "Benefits": ["benefits", "potential benefits"],
}


class RetrievalService:
    def __init__(self, cfg: Config = Config):
        self.cfg = cfg

    def _index_dir(self, index_id: str) -> str:
        return os.path.join(self.cfg.INDEXES_DIR, index_id)

    def _faiss_dir(self, index_id: str) -> str:
        return os.path.join(self._index_dir(index_id), "faiss")

    def _bm25_path(self, index_id: str) -> str:
        return os.path.join(self._index_dir(index_id), "bm25.json")

    def _load_faiss(self, index_id: str):
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Missing langchain-community or langchain-google-genai") from e

        embeddings = GoogleGenerativeAIEmbeddings(model=self.cfg.EMBED_MODEL)
        fdir = self._faiss_dir(index_id)
        if not os.path.isdir(fdir):
            raise FileNotFoundError("FAISS index folder not found; re-run ingest to index.")
        # allow_dangerous_deserialization is required for FAISS load_local
        vs = FAISS.load_local(fdir, embeddings=embeddings, index_name="index", allow_dangerous_deserialization=True)
        return vs

    def _load_docs_in_order(self, index_id: str, vs) -> List[Any]:
        """Return documents in the same order as chunks.json.

        We map chunk_id from chunks.json to documents in FAISS docstore by metadata.
        """
        chunks = read_json(os.path.join(self._index_dir(index_id), "chunks.json"), default=[]) or []
        # Build mapping from chunk_id to Document from FAISS docstore
        # FAISS docstore stores a dict of id->Document
        doc_by_chunk: Dict[str, Any] = {}
        try:
            # Newer LC
            values = vs.docstore._dict.values()
        except Exception:
            values = []
        for d in values:
            cid = (d.metadata or {}).get("chunk_id")
            if cid:
                doc_by_chunk[cid] = d
        ordered_docs: List[Any] = []
        for ch in chunks:
            cid = ch.get("chunk_id")
            d = doc_by_chunk.get(cid)
            if d is not None:
                ordered_docs.append(d)
        return ordered_docs

    @staticmethod
    def _normalize_scores(pairs: List[Tuple[int, float]]) -> Dict[int, float]:
        if not pairs:
            return {}
        vals = [s for _, s in pairs]
        lo, hi = min(vals), max(vals)
        if hi - lo <= 1e-9:
            return {i: 1.0 for i, _ in pairs}
        return {i: (s - lo) / (hi - lo) for i, s in pairs}

    def _allowed_heading(self, section, heading_norm: str) -> bool:
        if not section:
            return True
        hn = (heading_norm or "").strip().lower()
        if not hn:
            return True
        allowed = SECTION_ALLOWED_HEADINGS.get(section, [])
        return any(a in hn or hn in a for a in allowed)


    def _trim_text(self, text: str, max_tokens: int = 300) -> str:
        # Simple token-based trim
        if count_tokens(text) <= max_tokens:
            return text
        # binary trim by characters roughly proportional
        # fallback loop to avoid tiktoken heavy calls
        words = text.split()
        lo, hi = 0, len(words)
        best = text
        while lo < hi:
            mid = (lo + hi) // 2
            cand = " ".join(words[:mid])
            if count_tokens(cand) <= max_tokens:
                best = cand
                lo = mid + 1
            else:
                hi = mid
        return best

    def search(
        self,
        index_id: str,
        query: str,
        section: Optional[str] = None,
        # mode: 'dense' (default) uses vectorstore retriever only; 'hybrid' uses BM25+dense fusion
        mode: str = "dense",
        # Dense settings
        k_dense: int = 12,
        search_type: str = "mmr",
        search_kwargs: Optional[Dict[str, Any]] = None,
        # Hybrid settings
        k_sparse: int = 30,
        k_final: int = 12,
        w_sparse: float = 0.6,
        w_dense: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Run hybrid retrieval and return final snippets.

        Returns list of snippets with fields: chunk_id, page, section_path,
        heading_norm, text, score, source_scores.
        """
        vs = self._load_faiss(index_id)

        if mode == "dense":
            # Dense-only using LangChain retriever interface
            # Apply section-specific defaults if available and not explicitly overridden
            s_type = search_type
            skw = dict(search_kwargs or {})
            if section and not search_kwargs:
                try:
                    from app.config import Config as _C
                    sect_cfg = getattr(_C, "SECTION_RETRIEVAL_CONFIGS", {}).get(section)
                except Exception:
                    sect_cfg = None
                if sect_cfg:
                    s_type = sect_cfg.get("search_type", s_type)
                    skw.update(sect_cfg.get("search_kwargs", {}))
            skw.setdefault("k", k_dense)
            # Keep local cap aligned with requested k
            try:
                k_dense = int(skw.get("k", k_dense))
            except Exception:
                pass
            try:
                retriever = vs.as_retriever(search_type=s_type, search_kwargs=skw)
                docs = retriever.invoke(query)
                score_by_id = {}
            except Exception:
                # Fallback: similarity with scores
                docs_scores = vs.similarity_search_with_relevance_scores(query, k=k_dense)
                docs = [d for d, _ in docs_scores]
                score_by_id = {((d.metadata or {}).get("chunk_id")): float(s) for d, s in docs_scores}

            results: List[Dict[str, Any]] = []
            for rank, doc in enumerate(docs):
                md = doc.metadata or {}
                heading_norm = (md.get("heading_norm") or "").lower()
                if not self._allowed_heading(section, heading_norm):
                    continue
                page_span = md.get("page_span") or [1, 1]
                page = page_span[0]
                cid = md.get("chunk_id")
                score = score_by_id.get(cid, None)
                results.append(
                    {
                        "chunk_id": cid,
                        "page": int(page),
                        "section_path": md.get("section_path"),
                        "heading_norm": heading_norm,
                        "text": self._trim_text(doc.page_content or ""),
                        "score": score if score is not None else max(0.0, 1.0 - rank * 0.05),
                        "source_scores": {"sparse": 0.0, "dense": float(score) if score is not None else 0.0},
                    }
                )
                if len(results) >= k_dense:
                    break
            return results

        # Hybrid mode (BM25 + dense fusion)
        bm25 = load_bm25(self._bm25_path(index_id))
        docs_ordered = self._load_docs_in_order(index_id, vs)

        # Sparse candidates
        sparse_pairs = bm25_top_k(bm25, query, k=k_sparse)
        sparse_norm = self._normalize_scores(sparse_pairs)
        sparse_idx = {i for i, _ in sparse_pairs}

        # Dense candidates
        dense_results = vs.similarity_search_with_relevance_scores(query, k=k_dense)
        pos_by_cid = {((d.metadata or {}).get("chunk_id")): i for i, d in enumerate(docs_ordered)}
        dense_pairs: List[Tuple[int, float]] = []
        for d, score in dense_results:
            cid = (d.metadata or {}).get("chunk_id")
            if cid in pos_by_cid:
                dense_pairs.append((pos_by_cid[cid], float(score)))
        dense_norm = self._normalize_scores(dense_pairs)
        dense_idx = {i for i, _ in dense_pairs}

        # Fuse
        candidates = sorted(sparse_idx | dense_idx)
        fused: List[Tuple[int, float]] = []
        for i in candidates:
            s = sparse_norm.get(i, 0.0)
            d = dense_norm.get(i, 0.0)
            fused.append((i, w_sparse * s + w_dense * d))
        fused.sort(key=lambda x: x[1], reverse=True)

        # Build snippet results with filters
        results: List[Dict[str, Any]] = []
        for i, score in fused:
            if i < 0 or i >= len(docs_ordered):
                continue
            doc = docs_ordered[i]
            md = doc.metadata or {}
            heading_norm = (md.get("heading_norm") or "").lower()
            if not self._allowed_heading(section, heading_norm):
                continue
            page_span = md.get("page_span") or [1, 1]
            page = page_span[0]
            text = self._trim_text(doc.page_content or "")
            results.append(
                {
                    "chunk_id": md.get("chunk_id"),
                    "page": int(page),
                    "section_path": md.get("section_path"),
                    "heading_norm": heading_norm,
                    "text": text,
                    "score": score,
                    "source_scores": {
                        "sparse": float(sparse_norm.get(i, 0.0)),
                        "dense": float(dense_norm.get(i, 0.0)),
                    },
                }
            )
            if len(results) >= k_final:
                break

        return results
