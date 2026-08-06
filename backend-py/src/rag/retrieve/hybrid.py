from __future__ import annotations

from rag.config import config
from rag.ingest.embed import embed_one
from rag.store import lance


def _rrf_merge(
    dense: list[dict],
    sparse: list[dict],
    k: int,
    top_n: int,
) -> list[dict]:
    """Pure Reciprocal Rank Fusion merge — no I/O, fully testable."""
    scores: dict[str, dict] = {}

    def _add(results: list[dict]) -> None:
        for rank, item in enumerate(results):
            item_id = item.get("id", "")
            if not item_id:
                continue
            if item_id not in scores:
                scores[item_id] = {**item, "score_rrf": 0.0}
            scores[item_id]["score_rrf"] += 1.0 / (k + rank + 1)

    _add(dense)
    _add(sparse)
    return sorted(scores.values(), key=lambda x: x["score_rrf"], reverse=True)[:top_n]


async def hybrid_retrieve(query: str) -> list[dict]:
    """
    Hybrid retrieval:
    1. Dense vector search (BGE-M3), top-k=50
    2. BM25 full-text search, top-k=50
    3. Reciprocal Rank Fusion (RRF) merge with k=60
    Returns top-50 by RRF score.
    """
    import asyncio

    dense_k = config.retrieval.dense_top_k
    sparse_k = config.retrieval.sparse_top_k
    rrf_k = config.retrieval.rrf_k

    vector = await embed_one(query)

    dense_results, sparse_results = await asyncio.gather(
        lance.vector_search(vector, dense_k),
        lance.fts_search(query, sparse_k),
    )

    return _rrf_merge(dense_results, sparse_results, rrf_k, dense_k)
