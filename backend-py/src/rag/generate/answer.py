from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

from rag.config import LLM_SMALL_MODEL, config
from rag.generate.prompts import build_answer_prompt, build_no_context_prompt
from rag.llm import call_llm, call_llm_stream
from rag.logger import logger
from rag.retrieve.hybrid import hybrid_retrieve
from rag.retrieve.rerank import rerank

UUID_RE = re.compile(r"\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]", re.I)


@dataclass
class Citation:
    id: str
    doc_id: str
    source: str
    section_path: list[str]
    text_snippet: str


@dataclass
class QueryResponse:
    answer: str
    citations: list[Citation]
    retrieved: list[dict]
    invalid_citation_ids: list[str]
    timings_ms: dict[str, int]
    steps: list[str] = field(default_factory=list)


def is_corpus_empty() -> bool:
    try:
        from rag.store.lance import get_chunks_table
        table = get_chunks_table()
        return table.count_rows() == 0
    except Exception as exc:
        logger.warning("Failed to count chunks rows", error=str(exc))
        return False


async def _classify_query_intent(query: str, request_id: str | None = None) -> str:
    """
    Classify whether a query is 'general' (greetings, general chat, coding helper, general knowledge)
    or 'retrieval' (specific questions about documentation, APIs, uploaded guides, workspace).
    """
    # Heuristic first for ultra-fast response for simple greetings / tiny inputs
    clean_q = query.strip().lower().rstrip("?.!")
    greetings = {
        "hello", "hi", "hey", "hola", "greetings", "good morning", "good afternoon",
        "good evening", "how are you", "who are you", "what is your name", "help"
    }
    if clean_q in greetings or len(clean_q) < 4:
        return "general"

    prompt = (
        "You are a query router for a technical knowledge-base RAG application.\n"
        "Classify the user's query into one of two categories:\n"
        "- \"general\": The query is a greeting, general conversational response, standard general-knowledge question (e.g. \"what is the capital of France\"), or generic programming question (e.g. \"write a quicksort in python\") that does NOT require searching specific local document files.\n"
        "- \"retrieval\": The query is asking for specific technical documentation, configuration details, codebase structure, uploaded user guides, APIs, internal records, or domain-specific questions that require searching the local workspace knowledge base.\n\n"
        "Output EXACTLY one word: either \"general\" or \"retrieval\" and nothing else.\n\n"
        f"Query: {query}\n"
        "Category:"
    )

    try:
        category = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_SMALL_MODEL,
            temperature=0.0,
            max_tokens=5,
            request_id=request_id,
        )
        return category.strip().lower()
    except Exception as exc:
        logger.warning("Failed to classify query intent, defaulting to retrieval", error=str(exc))
        return "retrieval"


async def answer_query(
    query: str,
    request_id: str | None = None,
    top_k: int | None = None,
) -> QueryResponse:
    top_k = top_k or config.retrieval.rerank_top_k
    total_start = time.monotonic()

    steps = []
    def on_step(step_text: str):
        steps.append(step_text)

    from rag.logger import step_callback_var
    token = step_callback_var.set(on_step)
    try:
        # ── Check if corpus is empty or query is general ──────────────────────────
        if is_corpus_empty() or (await _classify_query_intent(query, request_id=request_id)) == "general":
            logger.info("Skipping retrieval — falling back to general knowledge directly")
            t0 = time.monotonic()
            prompt = build_no_context_prompt(query)
            answer_text = await call_llm(
                [{"role": "user", "content": prompt}],
                request_id=request_id,
            )
            llm_ms = int((time.monotonic() - t0) * 1000)
            return QueryResponse(
                answer=answer_text,
                citations=[],
                retrieved=[],
                invalid_citation_ids=[],
                timings_ms={
                    "embed_retrieve": 0,
                    "rerank": 0,
                    "llm": llm_ms,
                    "total": int((time.monotonic() - total_start) * 1000),
                },
                steps=steps,
            )

        # ── Retrieve ───────────────────────────────────────────────────────────────
        t0 = time.monotonic()
        candidates = await hybrid_retrieve(query)
        retrieve_ms = int((time.monotonic() - t0) * 1000)

        # ── Rerank ─────────────────────────────────────────────────────────────────
        t0 = time.monotonic()
        reranked = await rerank(query, candidates)
        rerank_ms = int((time.monotonic() - t0) * 1000)

        top_chunks = reranked[:top_k]

        # ── No retrieved context — answer from general knowledge ──────────────────
        if not top_chunks:
            logger.info("No context retrieved — falling back to general knowledge")
            t0 = time.monotonic()
            prompt = build_no_context_prompt(query)
            answer_text = await call_llm(
                [{"role": "user", "content": prompt}],
                request_id=request_id,
            )
            llm_ms = int((time.monotonic() - t0) * 1000)
            return QueryResponse(
                answer=answer_text,
                citations=[],
                retrieved=[],
                invalid_citation_ids=[],
                timings_ms={
                    "embed_retrieve": retrieve_ms,
                    "rerank": rerank_ms,
                    "llm": llm_ms,
                    "total": int((time.monotonic() - total_start) * 1000),
                },
                steps=steps,
            )

        # ── Low-confidence log (no longer a hard block) ────────────────────────
        best_score = top_chunks[0].get("score_rerank", 0.0)
        if best_score < 0.05:
            logger.warning(
                "Low rerank score — context may be weakly relevant, LLM will still answer",
                best_score=best_score,
            )

        # ── Generate ───────────────────────────────────────────────────────────────
        t0 = time.monotonic()
        prompt = build_answer_prompt(query, top_chunks)
        answer_text = await call_llm(
            [{"role": "user", "content": prompt}],
            request_id=request_id,
        )
        llm_ms = int((time.monotonic() - t0) * 1000)

        # ── Citation validation ────────────────────────────────────────────────────
        cited_ids = list(dict.fromkeys(m.group(1) for m in UUID_RE.finditer(answer_text)))
        valid_ids = {c["id"] for c in top_chunks}

        citations = [
            Citation(
                id=c["id"],
                doc_id=c["doc_id"],
                source=c["source"],
                section_path=c.get("section_path") or [],
                text_snippet=c["text"][:200],
            )
            for cid in cited_ids
            if cid in valid_ids
            for c in [next(x for x in top_chunks if x["id"] == cid)]
        ]

        invalid_ids = [cid for cid in cited_ids if cid not in valid_ids]
        if invalid_ids:
            logger.warning("Hallucinated citation IDs", ids=invalid_ids, request_id=request_id)

        return QueryResponse(
            answer=answer_text,
            citations=citations,
            retrieved=top_chunks,
            invalid_citation_ids=invalid_ids,
            timings_ms={
                "embed_retrieve": retrieve_ms,
                "rerank": rerank_ms,
                "llm": llm_ms,
                "total": int((time.monotonic() - total_start) * 1000),
            },
            steps=steps,
        )
    finally:
        step_callback_var.reset(token)


async def answer_query_stream(
    query: str,
    request_id: str | None = None,
    top_k: int | None = None,
) -> AsyncGenerator[str, None]:
    import asyncio
    top_k = top_k or config.retrieval.rerank_top_k
    total_start = time.monotonic()

    # ── Check if corpus is empty or query is general ──────────────────────────
    if is_corpus_empty() or (await _classify_query_intent(query, request_id=request_id)) == "general":
        logger.info("Skipping retrieval — falling back to general knowledge (stream)")
        t0 = time.monotonic()
        prompt = build_no_context_prompt(query)
        answer_text = ""
        async for token in call_llm_stream(
            [{"role": "user", "content": prompt}],
            request_id=request_id,
        ):
            answer_text += token
            yield _sse_event("delta", {"content": token})
        llm_ms = int((time.monotonic() - t0) * 1000)
        total_ms = int((time.monotonic() - total_start) * 1000)
        yield _sse_event("timings", {
            "embed_retrieve": 0,
            "rerank": 0,
            "llm": llm_ms,
            "total": total_ms,
        })
        yield _sse_event("citations", {"citations": []})
        yield _sse_event("retrieved", {"chunks": []})
        yield _sse_event("done", {})
        return

    # Queue for asynchronous communication between search background task and generator
    event_queue = asyncio.Queue()

    def on_step(step_text: str):
        event_queue.put_nowait(("status", {"message": step_text}))

    async def retrieve_and_rerank_task():
        try:
            # ── Retrieve ───────────────────────────────────────────────────────────────
            event_queue.put_nowait(("status", {"message": "Searching knowledge base..."}))
            t0 = time.monotonic()
            cands = await hybrid_retrieve(query)
            ret_ms = int((time.monotonic() - t0) * 1000)

            # ── Rerank ─────────────────────────────────────────────────────────────────
            event_queue.put_nowait(("status", {"message": "Reranking search results..."}))
            t0 = time.monotonic()
            reranked_cands = await rerank(query, cands)
            rerank_ms = int((time.monotonic() - t0) * 1000)

            event_queue.put_nowait(("result", (cands, reranked_cands, ret_ms, rerank_ms)))
        except Exception as e:
            event_queue.put_nowait(("error", e))

    from rag.logger import step_callback_var
    token = step_callback_var.set(on_step)

    # Spawn background task to perform search and rerank (it inherits the current ContextVar context)
    bg_task = asyncio.create_task(retrieve_and_rerank_task())

    candidates = []
    reranked = []
    retrieve_ms = 0
    rerank_ms = 0

    try:
        while True:
            ev_type, val = await event_queue.get()
            if ev_type == "status":
                yield _sse_event("status", val)
            elif ev_type == "result":
                candidates, reranked, retrieve_ms, rerank_ms = val
                break
            elif ev_type == "error":
                raise val
    finally:
        step_callback_var.reset(token)

    top_chunks = reranked[:top_k]

    if not top_chunks:
        logger.info("No context retrieved — falling back to general knowledge")
        yield _sse_event("status", {"message": "No relevant context found. Generating general answer..."})
        t0 = time.monotonic()
        prompt = build_no_context_prompt(query)
        answer_text = ""
        async for token in call_llm_stream(
            [{"role": "user", "content": prompt}],
            request_id=request_id,
        ):
            answer_text += token
            yield _sse_event("delta", {"content": token})
        llm_ms = int((time.monotonic() - t0) * 1000)
        total_ms = int((time.monotonic() - total_start) * 1000)
        yield _sse_event("timings", {
            "embed_retrieve": retrieve_ms,
            "rerank": rerank_ms,
            "llm": llm_ms,
            "total": total_ms,
        })
        yield _sse_event("citations", {"citations": []})
        yield _sse_event("retrieved", {"chunks": []})
        yield _sse_event("done", {})
        return

    best_score = top_chunks[0].get("score_rerank", 0.0)
    if best_score < 0.05:
        logger.warning(
            "Low rerank score — context may be weakly relevant",
            best_score=best_score,
        )

    yield _sse_event("status", {"message": "Context loaded. Generating RAG response..."})
    t0 = time.monotonic()
    prompt = build_answer_prompt(query, top_chunks)
    answer_text = ""
    async for token in call_llm_stream(
        [{"role": "user", "content": prompt}],
        request_id=request_id,
    ):
        answer_text += token
        yield _sse_event("delta", {"content": token})
    llm_ms = int((time.monotonic() - t0) * 1000)

    cited_ids = list(dict.fromkeys(m.group(1) for m in UUID_RE.finditer(answer_text)))
    valid_ids = {c["id"] for c in top_chunks}

    citations = [
        {
            "id": c["id"],
            "doc_id": c["doc_id"],
            "source": c["source"],
            "section_path": c.get("section_path") or [],
            "text_snippet": c["text"][:200],
        }
        for cid in cited_ids
        if cid in valid_ids
        for c in [next(x for x in top_chunks if x["id"] == cid)]
    ]

    invalid_ids = [cid for cid in cited_ids if cid not in valid_ids]
    if invalid_ids:
        logger.warning("Hallucinated citation IDs", ids=invalid_ids, request_id=request_id)

    total_ms = int((time.monotonic() - total_start) * 1000)
    yield _sse_event("timings", {
        "embed_retrieve": retrieve_ms,
        "rerank": rerank_ms,
        "llm": llm_ms,
        "total": total_ms,
    })
    yield _sse_event("citations", {"citations": citations, "invalid_citation_ids": invalid_ids})
    yield _sse_event("retrieved", {"chunks": top_chunks})
    yield _sse_event("done", {})


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
