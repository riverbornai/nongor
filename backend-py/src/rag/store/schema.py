from __future__ import annotations

import pyarrow as pa

VECTOR_DIM = 1024
INGEST_VERSION = "1.0.0"

CHUNKS_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string(), nullable=False),
        pa.field("doc_id", pa.string(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_type", pa.string(), nullable=False),
        pa.field("title", pa.string(), nullable=True),
        pa.field("section_path", pa.list_(pa.string()), nullable=True),
        pa.field("chunk_index", pa.int32(), nullable=False),
        pa.field("text", pa.string(), nullable=False),
        pa.field("contextual_text", pa.string(), nullable=False),
        pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM), nullable=False),
        pa.field("token_count", pa.int32(), nullable=False),
        pa.field("created_at", pa.string(), nullable=False),
        pa.field("ingest_version", pa.string(), nullable=False),
    ]
)

DOCUMENTS_SCHEMA = pa.schema(
    [
        pa.field("doc_id", pa.string(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_type", pa.string(), nullable=False),
        pa.field("title", pa.string(), nullable=True),
        pa.field("hash", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("error", pa.string(), nullable=True),
        pa.field("chunk_count", pa.int32(), nullable=False),
        pa.field("ingested_at", pa.string(), nullable=False),
    ]
)
