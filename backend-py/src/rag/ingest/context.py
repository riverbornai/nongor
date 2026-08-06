from __future__ import annotations

import asyncio

import tiktoken

from rag.config import LLM_SMALL_MODEL, config
from rag.llm import call_llm
from rag.logger import logger

enc = tiktoken.get_encoding("cl100k_base")

CONTEXT_PROMPT = """\
You are preparing a search-retrieval index. Given the full document and one
chunk from it, write a short standalone context (50–100 tokens) that situates
this chunk in the document: what section it belongs to, what entities or topic
it covers, and any references it depends on (e.g., "this paragraph continues
the discussion of X from section 2").

Do not summarize the chunk's content — only describe its position and
dependencies so a retrieval system can find it from queries that don't share
its exact wording.

<document>
{document_text}
</document>

<chunk>
{chunk_text}
</chunk>

Output only the context paragraph. No preamble.\
"""


def _truncate_doc(markdown: str, max_tokens: int) -> str:
    """Head + tail strategy: keep first 40k tokens, last 20k tokens."""
    tokens = enc.encode(markdown)
    if len(tokens) <= max_tokens:
        return markdown

    head = max_tokens * 2 // 3  # ~40k
    tail = max_tokens - head     # ~20k
    truncated = enc.decode(tokens[:head]) + "\n\n[... omitted ...]\n\n" + enc.decode(tokens[-tail:])
    return truncated


async def _generate_prefix(doc_text: str, chunk_text: str, idx: int, total: int) -> str:
    prompt = CONTEXT_PROMPT.format(
        document_text=_truncate_doc(doc_text, config.contextual_prefix.max_doc_tokens),
        chunk_text=chunk_text,
    )
    try:
        print(f"[SERVER STEP] LLM Contextual Prefix: Generating prefix for chunk {idx+1}/{total}...", flush=True)
        res = await call_llm(
            [{"role": "user", "content": prompt}],
            model=LLM_SMALL_MODEL,
            max_tokens=config.contextual_prefix.prefix_max_tokens,
        )
        print(f"[SERVER STEP] LLM Contextual Prefix: Finished chunk {idx+1}/{total} successfully.", flush=True)
        return res
    except Exception as exc:
        print(f"[SERVER STEP] LLM Contextual Prefix: Failed for chunk {idx+1}/{total}: {exc}", flush=True)
        logger.warning("Contextual prefix generation failed", error=str(exc))
        return ""


async def generate_prefixes(doc_text: str, chunk_texts: list[str]) -> list[str]:
    """
    Generate contextual prefixes for all chunks in parallel,
    batched at concurrency=8.
    """
    if not config.contextual_prefix.enabled:
        return [""] * len(chunk_texts)

    print(f"[SERVER STEP] Generating contextual LLM prefixes for {len(chunk_texts)} chunks (concurrency=8)...", flush=True)
    semaphore = asyncio.Semaphore(8)
    total = len(chunk_texts)

    async def bounded(text: str, idx: int) -> str:
        async with semaphore:
            return await _generate_prefix(doc_text, text, idx, total)

    res = await asyncio.gather(*[bounded(t, i) for i, t in enumerate(chunk_texts)])
    print(f"[SERVER STEP] Contextual LLM prefix generation complete for all {total} chunks!", flush=True)
    return res
