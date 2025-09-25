"""Lightweight BM25 utilities for sparse retrieval.

Simple Okapi BM25 build/search with whitespace tokenization. Designed to
persist/load as JSON alongside FAISS artifacts for hybrid retrieval.
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in text.split() if t.strip()]


def build_bm25_model(texts: List[str], k1: float = 1.5, b: float = 0.75) -> Dict[str, Any]:
    """Build a BM25 model from a list of texts."""
    N = len(texts)
    doc_tfs: List[Dict[str, int]] = []
    df = Counter()
    doc_lens = []
    for t in texts:
        toks = _tokenize(t)
        tf = Counter(toks)
        doc_tfs.append(dict(tf))
        doc_lens.append(len(toks))
        df.update(tf.keys())
    avgdl = (sum(doc_lens) / N) if N else 0.0
    idf: Dict[str, float] = {}
    for term, freq in df.items():
        # BM25 idf with log((N - df + 0.5)/(df + 0.5) + 1)
        idf[term] = math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)
    return {
        "k1": k1,
        "b": b,
        "N": N,
        "avgdl": avgdl,
        "idf": idf,
        "doc_tfs": doc_tfs,
        "doc_lens": doc_lens,
    }


def bm25_scores(model: Dict[str, Any], query: str) -> List[float]:
    q_terms = _tokenize(query)
    idf = model["idf"]
    k1 = model["k1"]
    b = model["b"]
    avgdl = model["avgdl"] or 1.0
    doc_tfs = model["doc_tfs"]
    doc_lens = model["doc_lens"]
    scores = [0.0] * len(doc_tfs)
    for i, tf in enumerate(doc_tfs):
        dl = doc_lens[i] or 1
        s = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            term_idf = idf.get(term, 0.0)
            f = tf[term]
            denom = f + k1 * (1 - b + b * (dl / avgdl))
            s += term_idf * ((f * (k1 + 1)) / denom)
        scores[i] = s
    return scores


def bm25_top_k(model: Dict[str, Any], query: str, k: int = 30) -> List[Tuple[int, float]]:
    scores = bm25_scores(model, query)
    idx = list(range(len(scores)))
    idx.sort(key=lambda i: scores[i], reverse=True)
    return [(i, scores[i]) for i in idx[:k] if scores[i] > 0.0]


def save_bm25(path: str, model: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f)


def load_bm25(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

