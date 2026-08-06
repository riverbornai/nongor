"""Unit tests for generate/answer.py intent-based routing and fast paths."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from rag.generate.answer import (
    _classify_query_intent,
    answer_query,
    answer_query_stream,
    is_corpus_empty,
)


@pytest.mark.asyncio
async def test_is_corpus_empty_handles_exception_safely():
    with patch("rag.store.lance.get_chunks_table", side_effect=Exception("Database failure")):
        assert is_corpus_empty() is False


@pytest.mark.asyncio
async def test_is_corpus_empty_true():
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 0
    with patch("rag.store.lance.get_chunks_table", return_value=mock_table):
        assert is_corpus_empty() is True


@pytest.mark.asyncio
async def test_is_corpus_empty_false():
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 42
    with patch("rag.store.lance.get_chunks_table", return_value=mock_table):
        assert is_corpus_empty() is False


@pytest.mark.asyncio
async def test_classify_query_intent_greetings():
    for greet in ["Hello", "hi", "hey!", "What is your name?", "Help"]:
        res = await _classify_query_intent(greet)
        assert res == "general"


@pytest.mark.asyncio
async def test_classify_query_intent_short():
    res = await _classify_query_intent("abc")
    assert res == "general"


@pytest.mark.asyncio
async def test_classify_query_intent_general_knowledge():
    with patch("rag.generate.answer.call_llm", new_callable=AsyncMock, return_value="general"):
        res = await _classify_query_intent("what is the capital of France?")
        assert res == "general"


@pytest.mark.asyncio
async def test_classify_query_intent_retrieval():
    with patch("rag.generate.answer.call_llm", new_callable=AsyncMock, return_value="retrieval"):
        res = await _classify_query_intent("how to configure OAuth inside the dashboard?")
        assert res == "retrieval"


@pytest.mark.asyncio
async def test_classify_query_intent_failure_fallback():
    with patch("rag.generate.answer.call_llm", side_effect=Exception("LLM down")):
        res = await _classify_query_intent("something here")
        assert res == "retrieval"


@pytest.mark.asyncio
async def test_answer_query_bypasses_retrieval_when_empty_corpus():
    with (
        patch("rag.generate.answer.is_corpus_empty", return_value=True),
        patch("rag.generate.answer.call_llm", new_callable=AsyncMock, return_value="Direct Answer") as mock_call,
        patch("rag.generate.answer.hybrid_retrieve", new_callable=AsyncMock) as mock_retrieve,
    ):
        res = await answer_query("What is up?")
        assert res.answer == "Direct Answer"
        assert res.timings_ms["embed_retrieve"] == 0
        assert res.timings_ms["rerank"] == 0
        mock_retrieve.assert_not_called()
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_answer_query_bypasses_retrieval_when_general_query():
    with (
        patch("rag.generate.answer.is_corpus_empty", return_value=False),
        patch("rag.generate.answer._classify_query_intent", new_callable=AsyncMock, return_value="general"),
        patch("rag.generate.answer.call_llm", new_callable=AsyncMock, return_value="General knowledge answer") as mock_call,
        patch("rag.generate.answer.hybrid_retrieve", new_callable=AsyncMock) as mock_retrieve,
    ):
        res = await answer_query("who are you?")
        assert res.answer == "General knowledge answer"
        assert res.timings_ms["embed_retrieve"] == 0
        assert res.timings_ms["rerank"] == 0
        mock_retrieve.assert_not_called()
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_answer_query_stream_bypasses_retrieval_when_general_query():
    async def mock_stream(*args, **kwargs):
        yield "Streaming "
        yield "General "
        yield "Response"

    with (
        patch("rag.generate.answer.is_corpus_empty", return_value=False),
        patch("rag.generate.answer._classify_query_intent", new_callable=AsyncMock, return_value="general"),
        patch("rag.generate.answer.call_llm_stream", side_effect=mock_stream) as mock_call,
        patch("rag.generate.answer.hybrid_retrieve", new_callable=AsyncMock) as mock_retrieve,
    ):
        events = []
        async for sse in answer_query_stream("Hello"):
            events.append(sse)

        mock_retrieve.assert_not_called()
        mock_call.assert_called_once()

        # Check SSE events
        assert any("status" in e and "Bypassing search" in e for e in events)
        assert any("status" in e and "Generating general response" in e for e in events)
        assert any("delta" in e and "Streaming" in e for e in events)
        assert any("timings" in e and "embed_retrieve\": 0" in e for e in events)
        assert any("citations" in e for e in events)
        assert any("retrieved" in e for e in events)
        assert any("done" in e for e in events)


@pytest.mark.asyncio
async def test_answer_query_stream_RAG_pipeline_emits_status_events():
    async def mock_stream(*args, **kwargs):
        yield "Chunk"

    mock_candidates = [{"id": "c1", "doc_id": "d1", "source": "s1.pdf", "text": "text"}]

    with (
        patch("rag.generate.answer.is_corpus_empty", return_value=False),
        patch("rag.generate.answer._classify_query_intent", new_callable=AsyncMock, return_value="retrieval"),
        patch("rag.generate.answer.hybrid_retrieve", new_callable=AsyncMock, return_value=mock_candidates),
        patch("rag.generate.answer.rerank", new_callable=AsyncMock, return_value=mock_candidates),
        patch("rag.generate.answer.call_llm_stream", side_effect=mock_stream),
    ):
        events = []
        async for sse in answer_query_stream(" RAG Query "):
            events.append(sse)

        assert any("status" in e and "Searching knowledge base" in e for e in events)
        assert any("status" in e and "Reranking search results" in e for e in events)
        assert any("status" in e and "Context loaded" in e for e in events)
        assert any("delta" in e and "Chunk" in e for e in events)
