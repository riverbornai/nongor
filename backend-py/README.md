# RAG PoC — Python Backend

High-accuracy local-first RAG system: ingests files/URLs, indexes with BGE-M3 + LanceDB, answers with verifiable citations.

> **The only outbound network traffic during queries is the LLM provider call.** All embedding, reranking, and storage run locally.

---

## Setup

**Requirements:** Python 3.11+, [uv](https://github.com/astral-sh/uv)

```bash
cd backend-py
cp .env.example .env        # fill in LLM_API_KEY
uv sync
```

Or run via Docker:

```bash
cp .env.example .env
docker-compose up -d
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | API key |
| `LLM_MODEL` | `deepseek-chat` | Model for answer generation |
| `LLM_SMALL_MODEL` | `deepseek-chat` | Model for contextual prefix generation |
| `LLM_PROVIDER` | — | Set to `local` to enforce private-only `LLM_BASE_URL` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Swapping LLM Providers

Same code, change env vars only:

**DeepSeek (default)**
```env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_SMALL_MODEL=deepseek-chat
```

**OpenAI**
```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1
LLM_SMALL_MODEL=gpt-4o-mini
```

**Ollama (local)**
```env
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
LLM_SMALL_MODEL=llama3
LLM_API_KEY=ollama
```

---

## Running the API

```bash
# Dev (auto-reload)
cd backend-py
python main.py

# Production
uvicorn rag.api.main:app --host 0.0.0.0 --port 8000
```

API docs at `http://localhost:8000/docs`

---

## Ingesting Documents

**CLI:**
```bash
python -m cli.ingest /path/to/document.pdf
python -m cli.ingest https://example.com/article
python -m cli.ingest /path/to/document.pdf --no-context   # skip contextual prefix
```

**API:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"source": "/path/to/document.pdf"}'
```

**File upload (browser / multipart):**
```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@/path/to/document.pdf"
```

Supported file types: `.pdf`, `.docx`, `.pptx`, `.html`, `.md`, `.txt`

---

## Querying

**CLI:**
```bash
python -m cli.query "What is X?"
```

**API:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is X?", "top_k": 8}'
```

**UI:** Navigate to `http://localhost:3000` (frontend dev server) or `http://localhost:8000/docs` for raw API.

---

## Smoke Test

Verify the LLM provider is reachable:

```bash
python -m cli.smoke "hello"
```

---

## Evaluation

```bash
# Populate eval/dataset.jsonl first (50–100 hand-labeled questions)
python -m eval.run
```

Results are written to `eval/results/<timestamp>.json`. Each run is compared to the previous — regressions ≥ 3% are flagged.

### Eval Results

| Metric | Value | Target |
|---|---|---|
| Retrieval Recall@5 | TBD | ≥ 0.85 |
| Retrieval Recall@10 | TBD | ≥ 0.92 |
| Answer faithfulness | TBD | ≥ 0.90 |
| Citation validity | TBD | ≥ 0.95 |

---

## Running Tests

```bash
uv sync --extra dev
pytest
```

---

## Architecture

```
Files / URLs → Parser → Chunker → Contextual Prefix (LLM) → BGE-M3 Embed → LanceDB
                                                                   ↓
Query → BGE-M3 Embed → Dense Search (top-50) ─┐
                     → BM25 FTS (top-50) ──────┤ RRF Merge → BGE Reranker (top-8) → LLM → Answer + Citations
```

- **Embeddings:** BGE-M3 (1024-dim, multilingual)
- **Reranker:** BGE-reranker-v2-m3 (cross-encoder)
- **Storage:** LanceDB (embedded, single folder on disk)
- **LLM:** Any OpenAI-compatible endpoint (swap via env vars)

---

## Data Layout

```
backend-py/
├── data/
│   ├── raw/          # source files (gitignored)
│   ├── lancedb/      # vector + FTS index (gitignored)
│   └── llm_calls.jsonl  # LLM cost log
```
