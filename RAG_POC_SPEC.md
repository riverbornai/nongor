# High-Accuracy RAG PoC — Engineering Spec

**Status:** Draft for implementation
**Owner:** (assign)
**Target:** Working, measurable PoC in ~7–10 engineer-days

---

## 1. Goal & Non-Goals

### Goal

Build a **local-first, high-accuracy RAG system** that ingests text files and URLs, indexes them, and answers questions with verifiable citations. Accuracy — not latency, not throughput — is the primary success metric.

### Why local-first

The system targets sensitive-data industries (legal, healthcare, defense). All retrieval, embedding, reranking, and storage **must run on a single machine with no network egress**. Only the generation LLM call leaves the box during the PoC, and that hop is designed to be swapped to a fully local model later with zero code changes.

### Non-goals (PoC scope)

- No image, audio, or video ingestion. Text and URL inputs only.
- No multi-user auth, no tenancy, no horizontal scaling.
- No fine-tuning. Off-the-shelf models only.
- No agentic decomposition / self-verification loop in v1 (architected for, deferred to v2).
- No production hardening (rate limiting, backups, observability beyond basic logs).

### Constraints

- Corpus size: **< 10,000 documents**.
- LLM provider: **anything OpenAI-API-compatible** (DeepSeek, OpenAI, vLLM, Ollama, LM Studio). Provider is a config flag; no provider-specific SDKs.
- One paid API key max (LLM provider). Everything else open-source and local.

---

## 2. Success Criteria

The PoC is "done" when **all** of the following hold on a hand-labeled eval set of 50–100 questions from the demo corpus:

| Metric                                             | Target                |
| -------------------------------------------------- | --------------------- |
| Retrieval Recall@5                                 | ≥ 0.85                |
| Retrieval Recall@10                                | ≥ 0.92                |
| Answer faithfulness (LLM-as-judge)                 | ≥ 0.90                |
| Answer has at least one valid citation             | 100%                  |
| Citation points to a chunk that supports the claim | ≥ 0.95                |
| End-to-end p50 query latency                       | ≤ 5s on demo hardware |

Numbers must be **reproducible via `python -m eval.run`** and committed to the repo.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                          │
│                                                                     │
│   Files / URLs ──▶ Parser ──▶ Markdown ──▶ Section-aware chunker    │
│   (pdf, docx,      (Docling /              (~400 tok, 50 overlap)   │
│    md, txt, html)   trafilatura)                  │                 │
│                                                   ▼                 │
│                                  Contextual prefix (LLM, small)     │
│                                                   │                 │
│                                ┌──────────────────┤                 │
│                                ▼                  ▼                 │
│                         BGE-M3 embed         BM25 tokenize          │
│                                │                  │                 │
│                                └────────┬─────────┘                 │
│                                         ▼                           │
│                                   ┌──────────────────────────┐      │
│                                   │       LanceDB            │      │
│                                   │  vector + FTS + meta     │      │
│                                   └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          QUERY PIPELINE                             │
│                                                                     │
│   query ──▶ Hybrid retrieval ──▶ Rerank ──▶ LLM (OpenAI-compat)     │
│             (dense top-50 +     (BGE-rerank   ──▶ answer +          │
│              BM25 top-50,         v2-m3,          [chunk_id]        │
│              RRF merge)           top-8)          citations         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

LLM call uses OpenAI client pointed at base_url from config.
→ DeepSeek, OpenAI, vLLM, Ollama all work with the same code.
```

---

## 4. Technology Stack

| Component                    | Tool                                   | Version | Purpose                                  |
| ---------------------------- | -------------------------------------- | ------- | ---------------------------------------- |
| Language                     | Python                                 | 3.11+   | All services                             |
| API framework                | FastAPI                                | latest  | `/ingest`, `/query` endpoints            |
| Document parser              | Docling                                | latest  | PDF, DOCX, PPTX, HTML → markdown         |
| URL fetcher                  | trafilatura                            | latest  | Web pages → clean text                   |
| HTML fetcher (JS pages)      | Playwright                             | latest  | Optional fallback for JS-rendered URLs   |
| Embeddings                   | BGE-M3 via `FlagEmbedding`             | latest  | 1024-dim multilingual dense vectors      |
| Sparse retrieval             | LanceDB native FTS (Tantivy/BM25)      | latest  | Lexical search, built into LanceDB       |
| Vector + FTS store           | LanceDB                                | latest  | Embedded, single-folder on disk          |
| Reranker                     | BGE-reranker-v2-m3 via `FlagEmbedding` | latest  | Cross-encoder rerank                     |
| LLM client                   | `openai` Python SDK                    | latest  | Points at any OpenAI-compatible endpoint |
| Tokenizer (for chunk sizing) | `tiktoken`                             | latest  | Approximate token counts                 |
| Eval                         | `ragas` (optional) + custom harness    | latest  | Recall@k, MRR, faithfulness              |
| Container                    | Docker + docker-compose                | —       | Reproducible runtime                     |

**LLM provider config (interchangeable):**

- DeepSeek: `base_url=https://api.deepseek.com/v1`, model `deepseek-chat` or `deepseek-reasoner`
- OpenAI: `base_url=https://api.openai.com/v1`, model `gpt-4.1` or `gpt-4o-mini`
- Local (later): `base_url=http://localhost:11434/v1` (Ollama) or vLLM endpoint

Same client code, swap via env var.

---

## 5. Repository Layout

```
rag-poc/
├── README.md
├── pyproject.toml                 # uv or poetry
├── docker-compose.yml             # app + lancedb volume
├── Dockerfile
├── .env.example
├── config.yaml                    # tunables (chunk size, top-k, model names)
│
├── src/rag/
│   ├── __init__.py
│   ├── config.py                  # Pydantic settings, env-driven
│   ├── llm.py                     # OpenAI-compatible client wrapper
│   │
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── parse.py               # Docling + trafilatura → markdown
│   │   ├── chunk.py               # section-aware + token-bounded chunking
│   │   ├── context.py             # LLM-generated contextual prefix
│   │   ├── embed.py               # BGE-M3 batch embedding
│   │   └── pipeline.py            # orchestrates parse→chunk→context→embed→write
│   │
│   ├── store/
│   │   ├── __init__.py
│   │   ├── schema.py              # LanceDB table schema
│   │   └── lance.py               # CRUD + hybrid query helpers
│   │
│   ├── retrieve/
│   │   ├── __init__.py
│   │   ├── hybrid.py              # dense + BM25 + RRF merge
│   │   └── rerank.py              # BGE-reranker-v2-m3
│   │
│   ├── generate/
│   │   ├── __init__.py
│   │   ├── prompts.py             # versioned prompt templates
│   │   └── answer.py              # LLM call with citation enforcement
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                # FastAPI app
│       └── schemas.py             # Pydantic request/response models
│
├── cli/
│   ├── ingest.py                  # python -m cli.ingest <path|url>
│   └── query.py                   # python -m cli.query "question"
│
├── eval/
│   ├── dataset.jsonl              # hand-labeled (query, expected_chunks, expected_answer)
│   ├── run.py                     # runs eval, prints metrics, writes results.json
│   ├── metrics.py                 # recall@k, MRR, faithfulness judge
│   └── judge_prompts.py
│
├── tests/
│   ├── test_chunk.py
│   ├── test_hybrid.py
│   ├── test_rerank.py
│   └── test_api.py
│
├── ui/                            # optional, minimal
│   └── index.html                 # simple query + citation viewer
│
└── data/                          # gitignored
    ├── raw/                       # source files dropped here
    └── lancedb/                   # persistent index
```

---

## 6. Data Model — LanceDB schema

Single table `chunks`:

| Field             | Type                           | Notes                                    |
| ----------------- | ------------------------------ | ---------------------------------------- |
| `id`              | string (UUID)                  | Primary key, used in citations           |
| `doc_id`          | string                         | Source document UUID                     |
| `source`          | string                         | Original path or URL                     |
| `source_type`     | string                         | `file` \| `url`                          |
| `title`           | string                         | Document title (best-effort)             |
| `section_path`    | list<string>                   | e.g. `["Chapter 2", "2.1 Background"]`   |
| `chunk_index`     | int                            | Order within document                    |
| `text`            | string                         | Raw chunk text (used for BM25 + display) |
| `contextual_text` | string                         | Prefix + text (used for embedding only)  |
| `vector`          | fixed_size_list<float32, 1024> | BGE-M3 dense embedding                   |
| `token_count`     | int                            | Approximate                              |
| `created_at`      | timestamp                      | Ingest time                              |
| `ingest_version`  | string                         | Schema/pipeline version tag              |

Indexes:

- IVF_PQ vector index on `vector` (or flat for <10k chunks — flat is fine and exact)
- Full-text index on `text` (LanceDB native FTS)

A separate `documents` table tracks ingest metadata (`doc_id`, `source`, `hash`, `status`, `error`, `chunk_count`, `ingested_at`) so re-ingest is idempotent on file hash.

---

## 7. Configuration (`config.yaml` + env)

```yaml
# config.yaml — defaults, overridable by env
chunk:
  target_tokens: 400
  overlap_tokens: 50
  min_tokens: 100 # drop chunks smaller than this after split

contextual_prefix:
  enabled: true
  max_doc_tokens: 60000 # truncate huge docs for prefix generation
  prefix_max_tokens: 100

embedding:
  model: BAAI/bge-m3
  batch_size: 32
  device: auto # cuda | mps | cpu

retrieval:
  dense_top_k: 50
  sparse_top_k: 50
  rrf_k: 60 # RRF constant
  rerank_top_k: 8

rerank:
  model: BAAI/bge-reranker-v2-m3
  batch_size: 16

llm:
  # All read from env; values here are documentation only.
  # base_url: env LLM_BASE_URL
  # api_key:  env LLM_API_KEY
  # model:    env LLM_MODEL
  temperature: 0.1
  max_output_tokens: 1500
  request_timeout_s: 60

store:
  path: ./data/lancedb
  table_chunks: chunks
  table_documents: documents

api:
  host: 0.0.0.0
  port: 8080
```

`.env.example`:

```
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-chat
LLM_SMALL_MODEL=deepseek-chat       # used for contextual prefixes
LOG_LEVEL=INFO
```

**Provider-swap rule:** anywhere the code calls the LLM, it must go through `src/rag/llm.py`, which constructs `OpenAI(base_url=..., api_key=...)` from env. No direct `openai.ChatCompletion` calls anywhere else.

---

## 8. Ingestion Pipeline — Detailed Spec

### 8.1 Parsing (`ingest/parse.py`)

- Input: file path OR URL.
- File types: `.pdf, .docx, .pptx, .html, .md, .txt`. Anything else → reject with clear error.
- PDFs/DOCX/PPTX/HTML → **Docling** → markdown string.
- URLs:
  1. Try `trafilatura.fetch_url` + `extract` (markdown=True).
  2. If empty or fails, fall back to Playwright headless → page HTML → trafilatura extract.
- Output: `ParsedDocument(doc_id, source, source_type, title, markdown, raw_metadata)`.
- Compute SHA-256 of normalized markdown; skip re-ingest if hash already in `documents` table.

### 8.2 Chunking (`ingest/chunk.py`)

Algorithm:

1. Parse markdown into a tree of sections by heading (`#`, `##`, `###`).
2. For each leaf section, split body by tokens with target=400, overlap=50, using `tiktoken` `cl100k_base` as a generic counter.
3. Never split across markdown table or fenced code block boundaries — keep these atomic even if they exceed target tokens (cap at 1200; log warning if exceeded).
4. Drop chunks below `min_tokens` UNLESS they are a standalone section heading + short body (keep those — useful for definitions).
5. Attach `section_path` (the chain of headings leading to the chunk).

Output: `list[Chunk]` with `text`, `section_path`, `chunk_index`.

### 8.3 Contextual Prefix (`ingest/context.py`)

For each chunk, generate a 50–100 token context describing where it sits in the document.

Prompt (`prompts.py::CONTEXT_PROMPT`):

```
You are preparing a search-retrieval index. Given the full document and one
chunk from it, write a short standalone context (50–100 tokens) that situates
this chunk in the document: what section it belongs to, what entities or topic
it covers, and any references it depends on (e.g., "this paragraph continues
the discussion of X from section 2").

Do not summarize the chunk's content — only describe its position and
dependencies so a retrieval system can find it from queries that don't share
its exact wording.

<document>
{full_document_markdown_truncated}
</document>

<chunk>
{chunk_text}
</chunk>

Output only the context paragraph. No preamble.
```

Implementation notes:

- Use `LLM_SMALL_MODEL`. For DeepSeek this is the same model; for OpenAI use `gpt-4o-mini`.
- Truncate document to `max_doc_tokens` (default 60k) — head + tail strategy: keep first 40k tokens, last 20k tokens, with a `[... omitted ...]` marker.
- Run in parallel with `asyncio.gather` batched at concurrency=8.
- On failure for any chunk, store empty prefix and log; do not fail the whole ingest.
- `contextual_text = prefix + "\n\n" + chunk.text` — this is what gets embedded.
- `text` (raw chunk) is what gets BM25-indexed and shown to the LLM at query time.

### 8.4 Embedding (`ingest/embed.py`)

- Model: BGE-M3 loaded once at process start (singleton).
- Embed `contextual_text` (not `text`) in batches of 32.
- Normalize vectors to unit length (cosine == dot product).
- Device auto-detect: CUDA → MPS → CPU.

### 8.5 Indexing (`store/lance.py`)

- Open or create LanceDB table per schema in §6.
- Upsert by `id`. On document re-ingest with same hash → no-op; with different hash → delete all chunks for `doc_id` then re-insert.
- After insert, build/refresh vector index (flat for <10k chunks; switch to IVF_PQ above that) and FTS index on `text`.

### 8.6 Ingest CLI / API

- CLI: `python -m cli.ingest <path|url> [--no-context]`
- API: `POST /ingest` with `{"source": "<path or url>"}` → `{"doc_id": "...", "chunk_count": N, "status": "ok"}`
- Both go through `ingest/pipeline.py::ingest_source(source) -> IngestResult`.

---

## 9. Retrieval Pipeline — Detailed Spec

### 9.1 Hybrid retrieval (`retrieve/hybrid.py`)

1. Embed query with BGE-M3 (same model as ingest).
2. Dense search: LanceDB vector search, top 50, cosine.
3. Sparse search: LanceDB FTS on `text`, top 50.
4. RRF merge:
   ```
   score(d) = sum over rankers r of  1 / (k + rank_r(d))
   k = 60
   ```
5. Return top 50 by RRF score.

### 9.2 Rerank (`retrieve/rerank.py`)

- Load BGE-reranker-v2-m3 once at startup.
- Score pairs `(query, chunk.text)` for the 50 candidates.
- Return top 8 by reranker score.
- Preserve original chunk metadata.

### 9.3 Response shape

```python
class RetrievedChunk(BaseModel):
    id: str
    doc_id: str
    source: str
    section_path: list[str]
    text: str
    score_rerank: float
    score_rrf: float
```

---

## 10. Generation — Detailed Spec

### 10.1 Prompt (`generate/prompts.py::ANSWER_PROMPT`)

```
You answer questions strictly from the provided context. Rules:

1. Use ONLY the context below. If the answer is not present, say
   "I don't have enough information to answer that." Do not guess.
2. Every factual claim must be followed by a citation in the form [id]
   where id matches a chunk_id from the context. Multiple citations: [id1][id2].
3. If multiple chunks disagree, surface the disagreement and cite each side.
4. Be concise. Do not pad with restatements of the question.

<context>
{context_blocks}
</context>

<question>
{user_question}
</question>

Answer:
```

`context_blocks` format, one per retrieved chunk:

```
[chunk_id: {id}]
source: {source}
section: {" > ".join(section_path)}
---
{text}
```

### 10.2 LLM call (`generate/answer.py`)

- Single call via `src/rag/llm.py` client.
- `temperature=0.1`, `max_tokens=1500`.
- After response: regex-extract `[<uuid>]` citations, validate each maps to a retrieved chunk; flag any "hallucinated" citation IDs in the response payload (do not fail the request — surface them).

### 10.3 Response shape

```python
class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]        # resolved chunks with source spans
    retrieved: list[RetrievedChunk]  # full top-8 for transparency
    invalid_citation_ids: list[str]  # any [id] not in retrieved set
    timings_ms: dict                 # embed, retrieve, rerank, llm, total
```

---

## 11. API Contracts

### `POST /ingest`

Request:

```json
{ "source": "/path/to/file.pdf" }
```

or

```json
{ "source": "https://example.com/article" }
```

Response:

```json
{
  "doc_id": "uuid",
  "source": "...",
  "title": "...",
  "chunk_count": 42,
  "status": "ok",
  "skipped_reason": null
}
```

Errors: 400 (unsupported type, bad URL), 422 (parse failed), 500.

### `POST /query`

Request:

```json
{ "query": "What is X?", "top_k": 8 }
```

Response: `QueryResponse` from §10.3.

### `GET /documents`

List ingested documents with chunk counts and ingest timestamps.

### `DELETE /documents/{doc_id}`

Remove all chunks and the document record.

### `GET /healthz`

`{"status": "ok"}` + model load status.

---

## 12. Evaluation Harness — Detailed Spec

### 12.1 Dataset (`eval/dataset.jsonl`)

Each line:

```json
{
  "id": "q001",
  "query": "What is the warranty period for product X?",
  "expected_chunk_ids": ["<id1>", "<id2>"],
  "expected_answer": "The warranty period is 24 months from the date of purchase.",
  "must_contain": ["24 months"],
  "must_not_contain": ["12 months", "lifetime"]
}
```

- 50–100 examples minimum.
- Hand-curated from the actual demo corpus.
- `expected_chunk_ids` populated after a first ingest run (eng picks the right chunks from the index).

### 12.2 Metrics (`eval/metrics.py`)

- **Retrieval**: Recall@5, Recall@10, MRR — using `expected_chunk_ids`.
- **Lexical**: `must_contain` / `must_not_contain` substring checks on answer.
- **Faithfulness (LLM-as-judge)**: for each (answer, retrieved_chunks) pair, ask the LLM:
  > "Is every factual claim in the answer supported by the cited chunks? Reply STRICTLY with one of: SUPPORTED, PARTIAL, UNSUPPORTED, and a one-sentence reason."
- **Citation validity**: % of `[id]` references that resolve to a retrieved chunk.

### 12.3 Runner (`eval/run.py`)

- Loads dataset, runs each query through `/query`, collects metrics.
- Writes `eval/results/<timestamp>.json` and a markdown summary table to stdout.
- Compares to last run; flags regressions ≥3% on any metric.

### 12.4 When to run

- Before adding any retrieval feature (baseline).
- After each Phase 4 change.
- In CI later (not v1 scope).

---

## 13. Logging & Observability (PoC-level)

- Structured logs (JSON) via `structlog`.
- Per-request `request_id` propagated through ingest and query.
- Log every LLM call: model, prompt tokens, completion tokens, latency. Persist to `data/llm_calls.jsonl` for cost analysis.
- No external APM. Stdout + file is fine.

---

## 14. Security / Privacy Notes

- LLM provider call is the **only** outbound network traffic during query. Document this prominently in README.
- Provide a `LLM_PROVIDER=local` mode that requires `LLM_BASE_URL` to be a private/loopback address; refuse to start if it points to a public domain.
- No telemetry. No analytics. No data sent anywhere except the configured LLM endpoint.
- Source documents stay on disk in `data/raw/`; LanceDB folder is the only derived store.

---

## 15. Implementation Plan — Phased Tasks

Each task lists **acceptance criteria** so PRs can be reviewed objectively.

### Phase 0 — Setup (0.5 day)

- [ ] **0.1** Initialize repo with layout from §5. `pyproject.toml` with all deps pinned. `ruff` + `mypy` configured.
  - _Acceptance:_ `uv sync` (or `poetry install`) succeeds; `ruff check` clean.
- [ ] **0.2** Implement `src/rag/config.py` (Pydantic settings) reading `config.yaml` + env.
  - _Acceptance:_ `python -c "from rag.config import settings; print(settings)"` prints resolved config.
- [ ] **0.3** Implement `src/rag/llm.py` — single OpenAI-compatible client.
  - _Acceptance:_ unit test mocks `OpenAI` constructor, asserts `base_url` and `api_key` come from env.
- [ ] **0.4** Smoke-test LLM provider with `python -m cli.smoke "hello"` — prints model name and a 1-token completion.
  - _Acceptance:_ works against DeepSeek and against OpenAI by changing env only.

### Phase 1 — Ingestion (1.5–2 days)

- [ ] **1.1** `parse.py` for files (Docling) and URLs (trafilatura, Playwright fallback).
  - _Acceptance:_ parses a sample PDF, DOCX, and URL each to non-empty markdown; rejects `.xyz` cleanly.
- [ ] **1.2** `chunk.py` per §8.2.
  - _Acceptance:_ unit tests assert (a) target token size respected within ±15%, (b) tables/code blocks never split, (c) section_path correct on a fixture markdown.
- [ ] **1.3** `store/schema.py` + `store/lance.py` — open/create tables, upsert chunks, idempotent on hash.
  - _Acceptance:_ ingesting the same file twice yields same `doc_id` and 0 new chunks.
- [ ] **1.4** `embed.py` with BGE-M3 singleton + batching.
  - _Acceptance:_ embeds 100 chunks in <10s on the dev machine; vectors are unit-norm.
- [ ] **1.5** `ingest/pipeline.py` orchestrator (skips contextual prefix when `--no-context`).
  - _Acceptance:_ `python -m cli.ingest sample.pdf --no-context` populates LanceDB.
- [ ] **1.6** `POST /ingest` + `GET /documents` + `DELETE /documents/{id}` endpoints.
  - _Acceptance:_ integration test ingests fixture and lists it.

### Phase 2 — Retrieval & generation baseline (1 day)

- [ ] **2.1** `retrieve/hybrid.py` — dense top-50, BM25 top-50, RRF merge.
  - _Acceptance:_ unit test on a fixture index returns expected ranking.
- [ ] **2.2** `generate/prompts.py` + `generate/answer.py` — LLM call with citation regex extraction.
  - _Acceptance:_ given fixture chunks, returns answer with at least one valid `[id]`.
- [ ] **2.3** `POST /query` endpoint returning full `QueryResponse`.
  - _Acceptance:_ end-to-end curl returns answer + citations + timings.
- [ ] **2.4** Minimal `ui/index.html` (vanilla JS) — query box, answer pane, citations clickable to show source chunk.
  - _Acceptance:_ demoable in browser at `http://localhost:8000`.

### Phase 3 — Eval harness (1 day, BEFORE Phase 4)

- [ ] **3.1** Pick or assemble demo corpus (~20–100 docs). Ingest it.
- [ ] **3.2** Hand-label `eval/dataset.jsonl` with 50–100 queries.
- [ ] **3.3** Implement `eval/metrics.py` (Recall@k, MRR, citation validity, faithfulness judge).
- [ ] **3.4** Implement `eval/run.py` runner + results writer.
  - _Acceptance:_ `python -m eval.run` prints a markdown table and writes `eval/results/<ts>.json`. **Numbers committed as the baseline.**

### Phase 4 — Accuracy upgrades, measured (2–3 days)

For each step: implement → run eval → record delta → keep or revert.

- [ ] **4.1** Add `retrieve/rerank.py` (BGE-reranker-v2-m3); plug into query path.
  - _Expected:_ +5–15% on Recall@5 (rerank improves top-k ordering more than recall, but contextual chunking helps both).
- [ ] **4.2** Add `ingest/context.py` (contextual prefix). Re-ingest corpus. Re-run eval.
  - _Expected:_ +10–25% on Recall@5 and faithfulness. This is usually the single biggest win.
- [ ] **4.3** Tune chunk size (300/400/600), overlap (25/50/100), rerank `top_k` (5/8/12). Pick best by eval.
- [ ] **4.4** Add "no context found" guardrail: if max rerank score < threshold, answer = "I don't have enough information…" without calling LLM. Threshold chosen from eval distribution.
  - _Acceptance:_ eval confirms reduced hallucination on out-of-corpus queries (add 10 such queries to the eval set).

### Phase 5 — Demo polish (1 day)

- [ ] **5.1** UI: show citation source on hover; click to scroll to chunk text; show retrieval scores.
- [ ] **5.2** `docker-compose.yml` running the API on port 8000 with `./data` volume.
- [ ] **5.3** README with: setup, env vars, how to ingest, how to query, how to swap LLM provider (3 examples: DeepSeek, OpenAI, Ollama), final eval numbers table.
- [ ] **5.4** Tag `v0.1-poc`. Hand off.

### Deferred (post-PoC, design hooks in v1)

- Agentic layer (query decomposition + verification loop) — keep `/query` as the atomic call it composes.
- Image ingestion (VLM) — `parse.py` already factored to accept new MIME types.
- Local LLM via Ollama/vLLM — already supported, just swap env vars.
- Multi-tenant + auth.
- Switch vector index from flat → IVF_PQ when corpus exceeds 50k chunks.
- Incremental re-ingest on file change.

---

## 16. Risks & Mitigations

| Risk                                                 | Likelihood | Impact | Mitigation                                                                                             |
| ---------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------ |
| Contextual prefix LLM cost balloons on large corpora | Med        | Med    | Run prefix on cheap model; cache by `(doc_hash, chunk_index)`; allow `--no-context` for bulk re-ingest |
| Docling fails on scanned PDFs                        | Med        | Med    | Document limitation; flag for future OCR fallback (Tesseract via Docling option)                       |
| Eval set too small → noisy metrics                   | High       | High   | Require min 50 examples; report confidence intervals via bootstrap in `eval/metrics.py`                |
| LLM hallucinates citations                           | Med        | High   | Validate every `[id]` against retrieved set; surface invalid ones; faithfulness judge in eval          |
| BGE-M3 cold start latency                            | Low        | Low    | Singleton load at app startup; readiness probe waits for it                                            |
| LanceDB schema migration mid-build                   | Med        | Med    | `ingest_version` tag on rows; migration script wipes + re-ingests for PoC                              |
| Provider lock-in creeping in                         | Low        | Med    | Lint rule: forbid `import openai` outside `src/rag/llm.py`                                             |

---

## 17. Estimated Effort

| Phase                              | Engineer-days |
| ---------------------------------- | ------------- |
| 0. Setup                           | 0.5           |
| 1. Ingestion                       | 2.0           |
| 2. Retrieval + generation baseline | 1.0           |
| 3. Eval harness                    | 1.0           |
| 4. Accuracy upgrades               | 2.5           |
| 5. Demo polish                     | 1.0           |
| **Total**                          | **~8 days**   |

One engineer full-time, or two engineers splitting ingestion / retrieval in parallel after Phase 0.

---

## 18. Open Questions for the Team

1. **Demo corpus** — what's the actual content the PoC needs to handle well? This determines parse-edge-case priority and eval question style.
2. **LLM budget for the PoC** — capping at DeepSeek (~$1–5 for full eval+demo) vs. OpenAI gpt-4.1 (~$20–100). Affects which model we use for contextual prefixes.
3. **Hardware target** — Apple Silicon laptop vs. Linux + NVIDIA box. Affects whether embeddings/rerank go via MPS or CUDA. Either works; just specify.
4. **Eval ownership** — who labels the 50–100 questions? This is the single most important artifact in the project. Cannot be skipped or outsourced to the model.
