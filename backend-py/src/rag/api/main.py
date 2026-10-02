from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from rag.api.schemas import (
    DocumentRecord,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)
from rag.config import ALLOWED_ORIGINS, config
from rag.generate.answer import answer_query, answer_query_stream
from rag.ingest.pipeline import ingest_buffer, ingest_source
from rag.logger import logger
from rag.store import lance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up LanceDB tables and log startup."""
    logger.info("Starting RAG API — warming up LanceDB tables...")
    lance.get_chunks_table()
    lance.get_docs_table()
    logger.info("LanceDB ready", chunks_table=config.store.table_chunks)
    yield
    logger.info("RAG API shutting down")


app = FastAPI(
    title="Knowledge Base Search — RAG API",
    description="High-accuracy RAG PoC: ingest files/URLs, query with citations.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /ingest ────────────────────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_path(request: IngestRequest):
    """Ingest a local file path or URL into the knowledge base."""
    try:
        result = await ingest_source(request.source)
        return IngestResponse(**result.__dict__)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Ingest failed", source=request.source, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


async def run_ingest_in_background(
    content: bytes,
    filename: str,
    content_type: str,
    use_prefix: bool,
    task_id: str,
):
    try:
        await ingest_buffer(
            content=content,
            filename=filename,
            content_type=content_type,
            use_prefix=use_prefix,
            task_id=task_id,
        )
    except Exception as exc:
        logger.error("Background ingest failed", filename=filename, error=str(exc))


@app.post("/ingest/upload", tags=["Ingestion"])
async def ingest_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_prefix: bool = True,
):
    """Upload a file directly from the browser (multipart/form-data) asynchronously."""
    content = await file.read()
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    from rag.ingest.pipeline import update_task_status
    update_task_status(task_id, "processing", "File upload done")
    
    # Add to background tasks
    background_tasks.add_task(
        run_ingest_in_background,
        content,
        file.filename or "upload",
        file.content_type or "application/octet-stream",
        use_prefix,
        task_id,
    )
    
    # Return immediately with the task info
    return {
        "task_id": task_id,
        "status": "processing",
        "step": "File upload done",
    }


@app.get("/ingest/status/{task_id}", tags=["Ingestion"])
async def get_ingest_status(task_id: str):
    """Get the current progress step of an asynchronous file ingestion task."""
    from rag.ingest.pipeline import ingestion_tasks
    task = ingestion_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Ingestion task not found")
    return task


# ── /query ─────────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(request: QueryRequest):
    """Query the knowledge base and get an answer with citations."""
    request_id = str(uuid.uuid4())
    try:
        result = await answer_query(
            query=request.query,
            request_id=request_id,
            top_k=request.top_k,
        )
        return QueryResponse(
            answer=result.answer,
            citations=[c.__dict__ for c in result.citations],
            retrieved=result.retrieved,
            invalid_citation_ids=result.invalid_citation_ids,
            timings_ms=result.timings_ms,
        )
    except Exception as exc:
        logger.error("Query failed", query=request.query, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query/stream", tags=["Query"])
async def query_stream(request: QueryRequest):
    """Query the knowledge base with streaming answer via SSE."""
    request_id = str(uuid.uuid4())

    async def event_generator():
        try:
            async for event_str in answer_query_stream(
                query=request.query,
                request_id=request_id,
                top_k=request.top_k,
            ):
                yield event_str
        except Exception as exc:
            logger.error("Streaming query failed", query=request.query, error=str(exc))
            import json
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ── /documents ─────────────────────────────────────────────────────────────────

@app.get("/documents", response_model=list[DocumentRecord], tags=["Documents"])
async def list_documents():
    """List all ingested documents with chunk counts and timestamps."""
    docs = await lance.list_documents()
    return docs


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """Remove a document and all its chunks from the knowledge base."""
    existing = await lance.get_document_by_id(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    deleted_chunks = await lance.delete_document(doc_id)
    logger.info("Document deleted", doc_id=doc_id, chunks_removed=deleted_chunks)
    return {"doc_id": doc_id, "chunks_removed": deleted_chunks, "status": "deleted"}


# ── /healthz ───────────────────────────────────────────────────────────────────

@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check — returns model load status."""
    from rag.ingest import embed as embed_mod
    from rag.retrieve import rerank as rerank_mod

    return HealthResponse(
        status="ok",
        models_loaded={
            "embedder": embed_mod._model is not None if embed_mod.get_active_service() == "local" else True,
            "reranker": rerank_mod._reranker is not None if rerank_mod.get_active_service() == "bge" else True,
        },
    )


# ── /settings ──────────────────────────────────────────────────────────────────

@app.get("/settings", response_model=SettingsResponse, tags=["Settings"])
async def get_settings():
    """Get the current settings of the RAG application."""
    from rag.ingest import embed as embed_mod
    from rag.retrieve import rerank as rerank_mod
    return SettingsResponse(
        embedding_service=embed_mod.get_active_service(),
        reranker_service=rerank_mod.get_active_service(),
    )


@app.post("/settings", response_model=SettingsResponse, tags=["Settings"])
async def update_settings(request: SettingsUpdateRequest):
    """Update settings, such as switching the active embedding or reranker service."""
    from rag.ingest import embed as embed_mod
    from rag.retrieve import rerank as rerank_mod
    try:
        if request.embedding_service is not None:
            embed_mod.set_active_service(request.embedding_service)
        if request.reranker_service is not None:
            rerank_mod.set_active_service(request.reranker_service)
        return SettingsResponse(
            embedding_service=embed_mod.get_active_service(),
            reranker_service=rerank_mod.get_active_service(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
