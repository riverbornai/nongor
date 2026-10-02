from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from rag.config import ROOT, config
from rag.logger import logger
from rag.store.schema import CHUNKS_SCHEMA, DOCUMENTS_SCHEMA, VECTOR_DIM

# ── LanceDB singletons ────────────────────────────────────────────────────────

_db: Any = None
_chunks_table: Any = None
_docs_table: Any = None
_fts_indexed: bool = False
_vector_indexed: bool = False


def _get_db_path() -> str:
    p = config.store.path
    if not Path(p).is_absolute():
        p = str(ROOT / p)
    return p


def _get_db() -> Any:
    global _db
    if _db is None:
        import lancedb

        db_path = _get_db_path()
        _db = lancedb.connect(db_path)
        logger.info("LanceDB connected", path=db_path)
    return _db


def get_chunks_table() -> Any:
    global _chunks_table
    if _chunks_table is None:
        db = _get_db()
        names = db.table_names()
        if config.store.table_chunks in names:
            _chunks_table = db.open_table(config.store.table_chunks)
        else:
            _chunks_table = db.create_table(
                config.store.table_chunks, schema=CHUNKS_SCHEMA
            )
            logger.info("Created chunks table")
    return _chunks_table


def get_docs_table() -> Any:
    global _docs_table
    if _docs_table is None:
        db = _get_db()
        names = db.table_names()
        if config.store.table_documents in names:
            _docs_table = db.open_table(config.store.table_documents)
        else:
            _docs_table = db.create_table(
                config.store.table_documents, schema=DOCUMENTS_SCHEMA
            )
            logger.info("Created documents table")
    return _docs_table


# ── Index helpers ─────────────────────────────────────────────────────────────

def ensure_fts_index() -> None:
    global _fts_indexed
    if _fts_indexed:
        return
    try:
        table = get_chunks_table()
        table.create_fts_index("text", replace=True)
        _fts_indexed = True
        logger.info("FTS index built on chunks.text")
    except Exception as exc:
        logger.warning("FTS index creation failed", error=str(exc))
        _fts_indexed = True  # Don't retry in a hot loop


def ensure_vector_index() -> None:
    """Build or refresh the vector index.
    Flat (exact) scan for <10k chunks; IVF_PQ above that threshold.
    """
    global _vector_indexed
    if _vector_indexed:
        return
    try:
        table = get_chunks_table()
        count = table.count_rows()
        if count >= 10_000:
            table.create_index(
                metric="cosine",
                num_partitions=256,
                num_sub_vectors=96,
                replace=True,
            )
            logger.info("IVF_PQ vector index built", rows=count)
        else:
            # <10k rows: LanceDB uses exact flat scan by default — no index needed
            logger.info("Corpus <10k chunks — using exact flat scan", rows=count)
        _vector_indexed = True
    except Exception as exc:
        logger.warning("Vector index creation skipped", error=str(exc))
        _vector_indexed = True  # Don't retry in a hot loop


# ── CRUD operations ───────────────────────────────────────────────────────────

async def get_document_by_hash(hash_: str) -> dict | None:
    def _query():
        table = get_docs_table()
        try:
            rows = (
                table.search(None)
                .where(f"hash = '{hash_}'", prefilter=True)
                .limit(1)
                .to_list()
            )
            return rows[0] if rows else None
        except Exception:
            return None

    return await asyncio.to_thread(_query)


async def get_document_by_id(doc_id: str) -> dict | None:
    def _query():
        table = get_docs_table()
        try:
            rows = (
                table.search(None)
                .where(f"doc_id = '{doc_id}'", prefilter=True)
                .limit(1)
                .to_list()
            )
            return rows[0] if rows else None
        except Exception:
            return None

    return await asyncio.to_thread(_query)


async def list_documents() -> list[dict]:
    def _query():
        import math

        table = get_docs_table()
        try:
            records = table.to_pandas().to_dict(orient="records")
            # pandas converts NULL → float('nan'); replace with None so Pydantic
            # can coerce values to str | None without a ResponseValidationError.
            return [
                {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}
                for row in records
            ]
        except Exception:
            return []

    return await asyncio.to_thread(_query)


async def upsert_document(doc: dict) -> None:
    def _write():
        table = get_docs_table()
        try:
            table.delete(f"doc_id = '{doc['doc_id']}'")
        except Exception:
            pass
        table.add([doc])

    await asyncio.to_thread(_write)


async def insert_chunks(chunks: list[dict]) -> None:
    if not chunks:
        return

    def _write():
        global _fts_indexed, _vector_indexed
        table = get_chunks_table()
        table.add(chunks)
        _fts_indexed = False
        _vector_indexed = False
        ensure_fts_index()
        ensure_vector_index()

    await asyncio.to_thread(_write)


async def delete_document(doc_id: str) -> int:
    """Delete document record and all its chunks. Returns number of chunks deleted."""

    def _delete():
        docs_table = get_docs_table()
        chunks_table = get_chunks_table()

        try:
            docs_table.delete(f"doc_id = '{doc_id}'")
        except Exception as exc:
            logger.warning("Delete document record failed", doc_id=doc_id, error=str(exc))

        try:
            before = chunks_table.count_rows()
            chunks_table.delete(f"doc_id = '{doc_id}'")
            after = chunks_table.count_rows()
            return before - after
        except Exception as exc:
            logger.warning("Delete chunks failed", doc_id=doc_id, error=str(exc))
            return 0

    return await asyncio.to_thread(_delete)


# ── Search ────────────────────────────────────────────────────────────────────

async def vector_search(vector: list[float], top_k: int) -> list[dict]:
    import numpy as np

    def _search():
        table = get_chunks_table()
        vec = np.array(vector, dtype=np.float32)
        return (
            table.search(vec, query_type="vector")
            .metric("cosine")
            .limit(top_k)
            .to_list()
        )

    return await asyncio.to_thread(_search)


async def fts_search(query: str, top_k: int) -> list[dict]:
    def _search():
        ensure_fts_index()
        table = get_chunks_table()
        try:
            return (
                table.search(query, query_type="fts")
                .limit(top_k)
                .to_list()
            )
        except Exception as exc:
            logger.warning("FTS search failed", error=str(exc))
            return []

    return await asyncio.to_thread(_search)
