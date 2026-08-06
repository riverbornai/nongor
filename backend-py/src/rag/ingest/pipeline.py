from __future__ import annotations

import uuid
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rag.ingest.chunk import chunk_markdown
from rag.ingest.context import generate_prefixes
from rag.ingest.embed import embed_batch_async
from rag.ingest.parse import ParsedDocument, parse_buffer, parse_source
from rag.logger import logger
from rag.store import lance

INGEST_VERSION = "1.0.0"

# Thread-safe dictionary to track the progress steps of background ingestion tasks
_tasks_lock = threading.Lock()
ingestion_tasks: dict[str, dict[str, Any]] = {}


def update_task_status(
    task_id: str,
    status: str,
    step: str,
    doc_id: str | None = None,
    chunk_count: int = 0,
    error: str | None = None,
):
    with _tasks_lock:
        ingestion_tasks[task_id] = {
            "task_id": task_id,
            "status": status,  # "processing" | "completed" | "failed"
            "step": step,
            "doc_id": doc_id,
            "chunk_count": chunk_count,
            "error": error,
        }


@dataclass
class IngestResult:
    doc_id: str
    source: str
    title: str
    chunk_count: int
    status: str
    skipped_reason: str | None = None


async def ingest_source(source: str, use_prefix: bool = True, task_id: str | None = None) -> IngestResult:
    """Ingest from a file path or URL string."""
    if task_id:
        update_task_status(task_id, "processing", "Parsing document...")
    doc = await parse_source(source)
    return await _ingest_doc(doc, use_prefix=use_prefix, task_id=task_id)


async def ingest_buffer(
    content: bytes, filename: str, content_type: str, use_prefix: bool = True, task_id: str | None = None
) -> IngestResult:
    """Ingest from an uploaded file buffer (multipart upload)."""
    if task_id:
        update_task_status(task_id, "processing", "Parsing document...")
    doc = await parse_buffer(content, filename, content_type)
    return await _ingest_doc(doc, use_prefix=use_prefix, task_id=task_id)


async def _ingest_doc(doc: ParsedDocument, use_prefix: bool, task_id: str | None = None) -> IngestResult:
    print(f"\n==================================================", flush=True)
    print(f"[PIPELINE START] Ingesting document: '{doc.title}' ({doc.source_type})", flush=True)
    print(f"==================================================", flush=True)
    
    try:
        # ── Idempotency check ──────────────────────────────────────────────────────
        print(f"[PIPELINE STEP 1/5] Checking document idempotency/hash...", flush=True)
        if task_id:
            update_task_status(task_id, "processing", "Checking document hash...")
        existing = await lance.get_document_by_hash(doc.sha256)
        if existing:
            print(f"[PIPELINE SKIP] Document hash matches existing record (ID: {existing['doc_id']}). Skipping re-ingest!\n", flush=True)
            logger.info(
                "Skipping re-ingest (hash unchanged)",
                source=doc.source,
                doc_id=existing["doc_id"],
            )
            if task_id:
                update_task_status(
                    task_id,
                    "completed",
                    "Ingestion complete (Skipped - Hash Unchanged)",
                    doc_id=existing["doc_id"],
                    chunk_count=existing["chunk_count"]
                )
            return IngestResult(
                doc_id=existing["doc_id"],
                source=doc.source,
                title=doc.title,
                chunk_count=existing["chunk_count"],
                status="skipped",
                skipped_reason="identical_hash",
            )

        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # ── Chunking ───────────────────────────────────────────────────────────────
        print(f"[PIPELINE STEP 2/5] Chunking markdown text...", flush=True)
        if task_id:
            update_task_status(task_id, "processing", "Chunking text...")
        chunks = chunk_markdown(doc.markdown)
        print(f" -> Document split into {len(chunks)} chunks.", flush=True)
        logger.info("Chunked document", source=doc.source, chunks=len(chunks))

        # ── Contextual prefixes (parallel, concurrency=8) ─────────────────────────
        print(f"[PIPELINE STEP 3/5] Generating contextual prefixes (use_prefix={use_prefix})...", flush=True)
        if task_id:
            update_task_status(task_id, "processing", "Generating contextual prefixes...")
        chunk_texts = [c.text for c in chunks]
        if use_prefix:
            prefixes = await generate_prefixes(doc.markdown, chunk_texts)
        else:
            print(" -> Contextual prefixes are disabled. Skipping LLM calls.", flush=True)
            prefixes = [""] * len(chunks)

        # ── Embedding (batched) ───────────────────────────────────────────────────
        print(f"[PIPELINE STEP 4/5] Preparing embedding contextual texts and computing vectors...", flush=True)
        if task_id:
            update_task_status(task_id, "processing", "Computing embeddings...")
        contextual_texts = [
            f"{prefix}\n\n{text}" if prefix else text
            for prefix, text in zip(prefixes, chunk_texts)
        ]
        vectors = await embed_batch_async(contextual_texts)

        # ── Build chunk records ────────────────────────────────────────────────────
        print(f"[PIPELINE STEP 5/5] Persisting document and chunks to LanceDB...", flush=True)
        if task_id:
            update_task_status(task_id, "processing", "Saving to database...")
        chunk_records = []
        for i, (chunk, prefix, ctx_text, vector) in enumerate(
            zip(chunks, prefixes, contextual_texts, vectors)
        ):
            chunk_records.append(
                {
                    "id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "source": doc.source,
                    "source_type": doc.source_type,
                    "title": doc.title,
                    "section_path": chunk.section_path,
                    "chunk_index": i,
                    "text": chunk.text,
                    "contextual_text": ctx_text,
                    "vector": vector,
                    "token_count": chunk.token_count,
                    "created_at": now,
                    "ingest_version": INGEST_VERSION,
                }
            )

        # ── Persist ────────────────────────────────────────────────────────────────
        doc_record = {
            "doc_id": doc_id,
            "source": doc.source,
            "source_type": doc.source_type,
            "title": doc.title,
            "hash": doc.sha256,
            "status": "ok",
            "error": None,
            "chunk_count": len(chunk_records),
            "ingested_at": now,
        }

        await lance.upsert_document(doc_record)
        await lance.insert_chunks(chunk_records)
        
        print(f"==================================================", flush=True)
        print(f"[PIPELINE SUCCESS] Document '{doc.title}' successfully ingested!", flush=True)
        print(f" -> Ingested ID: {doc_id}", flush=True)
        print(f" -> Total Chunks: {len(chunk_records)}", flush=True)
        print(f"==================================================\n", flush=True)

        logger.info(
            "Ingestion complete",
            source=doc.source,
            doc_id=doc_id,
            chunks=len(chunk_records),
        )

        if task_id:
            update_task_status(
                task_id,
                "completed",
                "Ingestion complete!",
                doc_id=doc_id,
                chunk_count=len(chunk_records)
            )

        return IngestResult(
            doc_id=doc_id,
            source=doc.source,
            title=doc.title,
            chunk_count=len(chunk_records),
            status="ok",
        )
    except Exception as exc:
        print(f"[PIPELINE ERROR] Ingestion failed: {exc}", flush=True)
        if task_id:
            update_task_status(task_id, "failed", f"Failed: {str(exc)}", error=str(exc))
        raise
