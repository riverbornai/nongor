from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import numpy as np
import torch

from rag.config import config
from rag.logger import logger

_model: Any = None
_active_service: str = "local"


def get_active_service() -> str:
    """Get the current active embedding service ("local" or "openai")."""
    return _active_service


def set_active_service(service: str) -> None:
    """Change the active embedding service ("local" or "openai")."""
    global _active_service
    if service not in ("local", "openai"):
        raise ValueError(f"Unsupported embedding service: {service}")
    _active_service = service
    logger.info("Active embedding service changed", service=service)


def _get_device() -> str | None:
    cfg_device = getattr(config.embedding, "device", "auto")
    if cfg_device in ("cuda", "cpu"):
        return cfg_device
    if cfg_device == "mps":
        return "mps"

    if torch.cuda.is_available():
        return "cuda"
    # Note: We deliberately avoid defaulting to 'mps' here because FlagEmbedding/PyTorch
    # has known freezing/hanging bugs on Apple Silicon MPS with certain operators.
    # We default to CPU (None) for stability.
    return None


def _load_model() -> Any:
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel

        device = _get_device()
        print(f"\n[SERVER STEP] Loading BGE-M3 Embedding Model on '{device or 'cpu'}'...", flush=True)
        print(" -> NOTE: The first load might take a few minutes if HuggingFace needs to download the 1.2GB weights...", flush=True)
        logger.info("Loading BGE-M3 embedding model", model=config.embedding.model, device=device or "cpu")
        
        # CPU does not fully support float16 operations in PyTorch, so use fp16 only on CUDA/MPS
        use_fp16 = device in ("cuda", "mps")
        
        _model = BGEM3FlagModel(
            config.embedding.model,
            use_fp16=use_fp16,
            devices=[device] if device else None,
        )
        print("[SERVER STEP] BGE-M3 Embedding Model successfully loaded!\n", flush=True)
        logger.info("BGE-M3 model loaded")
    return _model


def embed_batch_local(texts: list[str]) -> list[list[float]]:
    """Embed texts locally using BGE-M3."""
    model = _load_model()
    print(f"[SERVER STEP] Computing BGE-M3 embeddings for {len(texts)} chunks (batch size: {config.embedding.batch_size})...", flush=True)
    output = model.encode(
        texts,
        batch_size=config.embedding.batch_size,
        max_length=8192,
    )
    dense: np.ndarray = output["dense_vecs"]  # shape (N, 1024), already normalized by BGE-M3
    print(f"[SERVER STEP] Embeddings generated successfully!", flush=True)
    return dense.tolist()


def embed_batch_openai(texts: list[str]) -> list[list[float]]:
    """Embed texts in the cloud using OpenAI text-embedding-3-small (truncated to 1024)."""
    import os
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable to use OpenAI embeddings.")

    client = OpenAI(api_key=api_key)
    print(f"[SERVER STEP] Computing OpenAI cloud embeddings for {len(texts)} chunks...", flush=True)
    
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
        dimensions=1024,
    )
    print(f"[SERVER STEP] OpenAI embeddings generated successfully!", flush=True)
    
    # Extract the embeddings and sort them by index to guarantee ordering
    embeddings = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
    return embeddings


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts in batches. Returns list of unit-norm float32 vectors.
    Dispatches to either the local BGE-M3 model or OpenAI cloud service depending on active setting.
    """
    if _active_service == "openai":
        return embed_batch_openai(texts)
    else:
        return embed_batch_local(texts)


async def embed_batch_async(texts: list[str]) -> list[list[float]]:
    """Async wrapper — runs embedding in a thread pool to avoid blocking the event loop."""
    return await asyncio.to_thread(embed_batch, texts)


async def embed_one(text: str) -> list[float]:
    """Convenience: embed a single string."""
    results = await embed_batch_async([text])
    return results[0]
