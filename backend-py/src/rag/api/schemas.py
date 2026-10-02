from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class IngestRequest(BaseModel):
    source: str  # file path or URL


class IngestResponse(BaseModel):
    doc_id: str
    source: str
    title: str
    chunk_count: int
    status: str
    skipped_reason: str | None = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 8


class Citation(BaseModel):
    id: str
    doc_id: str
    source: str
    section_path: list[str]
    text_snippet: str


class RetrievedChunk(BaseModel):
    id: str
    doc_id: str
    source: str
    section_path: list[str] = []
    text: str
    score_rerank: float = 0.0
    score_rrf: float = 0.0


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved: list[dict]
    invalid_citation_ids: list[str]
    timings_ms: dict[str, int]
    steps: list[str] = []


class DocumentRecord(BaseModel):
    doc_id: str
    source: str
    source_type: str
    title: str | None
    hash: str
    status: str
    error: str | None
    chunk_count: int
    ingested_at: str


class HealthResponse(BaseModel):
    status: str
    models_loaded: dict[str, bool]


class SettingsResponse(BaseModel):
    embedding_service: str
    reranker_service: str


class SettingsUpdateRequest(BaseModel):
    embedding_service: str | None = None
    reranker_service: str | None = None

