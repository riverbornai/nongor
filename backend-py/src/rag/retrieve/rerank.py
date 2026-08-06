from __future__ import annotations

import asyncio
from typing import Any

import torch

from rag.config import config
from rag.logger import logger

_reranker: Any = None
_active_service: str = "bge"  # "bge" or "openai"


def get_active_service() -> str:
    """Get the active reranker service ("bge" or "openai")."""
    return _active_service


def set_active_service(service: str) -> None:
    """Change the active reranker service ("bge" or "openai")."""
    global _active_service
    if service not in ("bge", "openai"):
        raise ValueError(f"Unsupported reranker service: {service}")
    _active_service = service
    logger.info("Active reranker service changed", service=service)


def _get_device() -> str | None:
    cfg_device = getattr(config.rerank, "device", "auto") if hasattr(config, "rerank") else "auto"
    if cfg_device in ("cuda", "cpu"):
        return cfg_device
    if cfg_device == "mps":
        return "mps"

    if torch.cuda.is_available():
        return "cuda"
    # Note: Avoid defaulting to 'mps' here because FlagEmbedding/PyTorch has known
    # freezing/hanging bugs on Apple Silicon MPS with certain operators.
    # Default to CPU (None) for stability.
    return None


def _load_reranker() -> Any:
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker

        device = _get_device()
        print(f"\n[SERVER STEP] Loading BGE Reranker Model on '{device or 'cpu'}'...", flush=True)
        print(" -> NOTE: The first load might take a few minutes if HuggingFace needs to download the weights...", flush=True)
        logger.info("Loading BGE reranker", model=config.rerank.model, device=device or "cpu")
        
        # CPU does not fully support float16 operations in PyTorch, so use fp16 only on CUDA/MPS
        use_fp16 = device in ("cuda", "mps")
        
        _reranker = FlagReranker(
            config.rerank.model,
            use_fp16=use_fp16,
            devices=[device] if device else None,
        )
        print("[SERVER STEP] BGE Reranker Model successfully loaded!\n", flush=True)
        logger.info("BGE reranker loaded")
    return _reranker


def _rerank_sync(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Score (query, chunk.text) pairs with the cross-encoder reranker."""
    reranker = _load_reranker()
    pairs = [[query, c["text"]] for c in candidates]

    # Batch scoring
    scores = reranker.compute_score(pairs, normalize=True)

    if isinstance(scores, float):
        scores = [scores]

    ranked = sorted(
        [
            {**cand, "score_rerank": float(score)}
            for cand, score in zip(candidates, scores)
        ],
        key=lambda x: x["score_rerank"],
        reverse=True,
    )
    return ranked[:top_k]


def _rerank_openai(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """
    Rerank candidates using an OpenAI LLM (gpt-4o-mini) as a reranker.
    Asks the LLM to score the relevance of each candidate chunk.
    """
    import os
    import json
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable to use OpenAI reranking.")

    client = OpenAI(api_key=api_key)
    
    # We construct a highly optimized prompt listing the candidates with their IDs
    candidate_data = []
    for idx, c in enumerate(candidates):
        candidate_data.append({
            "index": idx,
            "text": c["text"]
        })

    prompt = f"""You are an advanced search relevance engine.
Your task is to evaluate the relevance of the following candidate document chunks to the user's query.

Query: "{query}"

Candidates to evaluate:
{json.dumps(candidate_data, indent=2)}

Assign a relevance score between 0.0 (completely irrelevant) and 1.0 (highly relevant) to each candidate chunk.
Respond ONLY with a JSON object containing a list under the key "rankings" where each item has "index" (integer) and "score" (float).
Example output:
{{
  "rankings": [
    {{"index": 0, "score": 0.95}},
    {{"index": 1, "score": 0.42}}
  ]
}}
"""

    try:
        print(f"[SERVER STEP] Asking OpenAI cloud (gpt-4o-mini) to rerank {len(candidates)} candidates...", flush=True)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise document ranking assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=1500,
        )

        raw_json = resp.choices[0].message.content or ""
        data = json.loads(raw_json)
        rankings = data.get("rankings", [])

        # Map back to original candidates and assign scores
        score_by_index = {item["index"]: item["score"] for item in rankings if "index" in item and "score" in item}

        ranked = []
        for idx, cand in enumerate(candidates):
            score = score_by_index.get(idx, 0.0)
            ranked.append({**cand, "score_rerank": float(score)})

        ranked = sorted(ranked, key=lambda x: x["score_rerank"], reverse=True)
        print(f"[SERVER STEP] OpenAI reranking complete!", flush=True)
        return ranked[:top_k]

    except Exception as exc:
        print(f"[SERVER STEP] OpenAI reranking failed: {str(exc)}. Falling back to direct RRF scores...", flush=True)
        logger.warning("OpenAI reranking failed", error=str(exc))
        # Fallback to bypass logic
        ranked = []
        for cand in candidates:
            score = cand.get("score_rrf", cand.get("score", 1.0))
            ranked.append({**cand, "score_rerank": float(score)})
        return ranked[:top_k]


async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    Rerank candidates using BGE-reranker or OpenAI cloud-reranker depending on active setting.
    """
    top_k = config.retrieval.rerank_top_k
    if not candidates:
        return []

    if _active_service == "openai":
        return await asyncio.to_thread(_rerank_openai, query, candidates, top_k)
    else:
        return await asyncio.to_thread(_rerank_sync, query, candidates, top_k)
