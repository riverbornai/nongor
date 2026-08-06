from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from the project root (backend-py/) before reading any env vars
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import yaml
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]  # backend-py/src/rag/config.py -> backend-py/


class ChunkConfig(BaseModel):
    target_tokens: int = 400
    overlap_tokens: int = 50
    min_tokens: int = 100


class ContextualPrefixConfig(BaseModel):
    enabled: bool = True
    max_doc_tokens: int = 60000
    prefix_max_tokens: int = 100


class EmbeddingConfig(BaseModel):
    model: str = "BAAI/bge-m3"
    batch_size: int = 32
    device: str = "auto"


class RetrievalConfig(BaseModel):
    dense_top_k: int = 50
    sparse_top_k: int = 50
    rrf_k: int = 60
    rerank_top_k: int = 8


class RerankConfig(BaseModel):
    model: str = "BAAI/bge-reranker-v2-m3"
    batch_size: int = 16


class LlmConfig(BaseModel):
    temperature: float = 0.1
    max_output_tokens: int = 1500
    request_timeout_s: int = 60


class StoreConfig(BaseModel):
    path: str = "./data/lancedb"
    table_chunks: str = "chunks"
    table_documents: str = "documents"


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    chunk: ChunkConfig = ChunkConfig()
    contextual_prefix: ContextualPrefixConfig = ContextualPrefixConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    rerank: RerankConfig = RerankConfig()
    llm: LlmConfig = LlmConfig()
    store: StoreConfig = StoreConfig()
    api: ApiConfig = ApiConfig()


def load_config() -> AppConfig:
    config_path = ROOT / "config.yaml"
    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
    return AppConfig(**raw)


config = load_config()

# Environment variables
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
LLM_SMALL_MODEL: str = os.getenv("LLM_SMALL_MODEL", "gpt-4o-mini")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# CORS origins (comma-separated string -> list)
_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _origins.split(",") if o.strip()]
