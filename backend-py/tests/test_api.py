"""Integration tests for FastAPI endpoints — mocks DB and pipeline."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with (
        patch("rag.store.lance.get_chunks_table", return_value=MagicMock()),
        patch("rag.store.lance.get_docs_table", return_value=MagicMock()),
    ):
        from rag.api.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── /healthz ───────────────────────────────────────────────────────────────────

def test_healthz_returns_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "models_loaded" in data
    assert "embedder" in data["models_loaded"]
    assert "reranker" in data["models_loaded"]


# ── /ingest ────────────────────────────────────────────────────────────────────

def test_ingest_unsupported_file_type_returns_400(client):
    with patch(
        "rag.api.main.ingest_source",
        new_callable=AsyncMock,
        side_effect=ValueError("Unsupported file type '.xyz'"),
    ):
        resp = client.post("/ingest", json={"source": "file.xyz"})
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


def test_ingest_ok_returns_doc_id(client):
    mock_result = MagicMock()
    mock_result.__dict__ = {
        "doc_id": "abc-123", "source": "doc.pdf", "title": "Doc",
        "chunk_count": 12, "status": "ok", "skipped_reason": None,
    }
    with patch("rag.api.main.ingest_source", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post("/ingest", json={"source": "doc.pdf"})
    assert resp.status_code == 200
    assert resp.json()["doc_id"] == "abc-123"
    assert resp.json()["chunk_count"] == 12


def test_ingest_skipped_has_skipped_reason(client):
    mock_result = MagicMock()
    mock_result.__dict__ = {
        "doc_id": "abc-123", "source": "doc.pdf", "title": "Doc",
        "chunk_count": 5, "status": "skipped", "skipped_reason": "identical_hash",
    }
    with patch("rag.api.main.ingest_source", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post("/ingest", json={"source": "doc.pdf"})
    assert resp.status_code == 200
    assert resp.json()["skipped_reason"] == "identical_hash"


# ── /query ─────────────────────────────────────────────────────────────────────

def test_query_returns_answer_and_citations(client):
    mock_result = MagicMock()
    mock_result.answer = "The answer is X. [abc-def-123]"
    mock_result.citations = []
    mock_result.retrieved = []
    mock_result.invalid_citation_ids = []
    mock_result.timings_ms = {"embed_retrieve": 100, "rerank": 50, "llm": 300, "total": 450}

    with patch("rag.api.main.answer_query", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post("/query", json={"query": "What is X?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert "timings_ms" in data


# ── /documents ─────────────────────────────────────────────────────────────────

def test_list_documents_returns_list(client):
    with patch("rag.store.lance.list_documents", new_callable=AsyncMock, return_value=[]):
        resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_document_not_found_returns_404(client):
    with patch("rag.store.lance.get_document_by_id", new_callable=AsyncMock, return_value=None):
        resp = client.delete("/documents/nonexistent-id")
    assert resp.status_code == 404


def test_delete_document_ok(client):
    fake_doc = {"doc_id": "uuid-1", "source": "f.pdf", "title": "F"}
    with (
        patch("rag.store.lance.get_document_by_id", new_callable=AsyncMock, return_value=fake_doc),
        patch("rag.store.lance.delete_document", new_callable=AsyncMock, return_value=5),
    ):
        resp = client.delete("/documents/uuid-1")
    assert resp.status_code == 200
    assert resp.json()["chunks_removed"] == 5
