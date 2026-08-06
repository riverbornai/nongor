"""Unit tests for retrieve/rerank.py — mocks FlagReranker to avoid model loading."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


def _candidate(id_: str, text: str = "text") -> dict:
    return {"id": id_, "doc_id": "d", "source": "f.txt", "section_path": [], "text": text}


@pytest.fixture(autouse=True)
def reset_reranker():
    """Reset the singleton reranker between tests."""
    import rag.retrieve.rerank as mod
    original = mod._reranker
    yield
    mod._reranker = original


@pytest.mark.asyncio
async def test_rerank_returns_top_k_results():
    mock_reranker = MagicMock()
    mock_reranker.compute_score.return_value = [0.9, 0.2, 0.7, 0.4, 0.6]

    import rag.retrieve.rerank as mod
    mod._reranker = mock_reranker

    from rag.retrieve.rerank import rerank
    from rag.config import config
    config.retrieval.rerank_top_k = 3

    candidates = [_candidate(f"id{i}") for i in range(5)]
    result = await rerank("what is X?", candidates)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_rerank_sorted_descending_by_score():
    mock_reranker = MagicMock()
    mock_reranker.compute_score.return_value = [0.1, 0.9, 0.5]

    import rag.retrieve.rerank as mod
    mod._reranker = mock_reranker

    from rag.retrieve.rerank import rerank
    from rag.config import config
    config.retrieval.rerank_top_k = 3

    candidates = [_candidate(f"id{i}") for i in range(3)]
    result = await rerank("query", candidates)
    scores = [r["score_rerank"] for r in result]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_rerank_empty_candidates():
    from rag.retrieve.rerank import rerank
    result = await rerank("query", [])
    assert result == []


@pytest.mark.asyncio
async def test_rerank_attaches_score_rerank_field():
    mock_reranker = MagicMock()
    mock_reranker.compute_score.return_value = [0.75, 0.25]

    import rag.retrieve.rerank as mod
    mod._reranker = mock_reranker

    from rag.retrieve.rerank import rerank
    from rag.config import config
    config.retrieval.rerank_top_k = 2

    candidates = [_candidate("a"), _candidate("b")]
    result = await rerank("query", candidates)
    for r in result:
        assert "score_rerank" in r
        assert isinstance(r["score_rerank"], float)
