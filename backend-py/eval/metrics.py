from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval.judge_prompts import FAITHFULNESS_PROMPT
from rag.generate.answer import QueryResponse
from rag.llm import call_llm


def recall_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> float:
    """Recall@k: fraction of expected chunks found in top-k retrieved."""
    if not expected_ids:
        return 1.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & expected_ids) / len(expected_ids)


def mrr(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant chunk."""
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in expected_ids:
            return 1.0 / rank
    return 0.0


def citation_validity(resp: QueryResponse) -> float:
    """% of [id] citations in the answer that resolve to a retrieved chunk."""
    all_cited = len(resp.citations) + len(resp.invalid_citation_ids)
    if all_cited == 0:
        return 1.0
    return len(resp.citations) / all_cited


def bootstrap_ci(
    values: list[float],
    statistic: Callable[[list[float]], float] | None = None,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Bootstrap confidence interval for a statistic (default: mean).
    Returns (lower, upper) at the given confidence level.
    """
    if not values:
        return (0.0, 0.0)
    if statistic is None:
        statistic = lambda x: sum(x) / len(x)

    n = len(values)
    rng = random.Random(42)
    bootstrap_stats = sorted(
        statistic([rng.choice(values) for _ in range(n)])
        for _ in range(n_bootstrap)
    )
    alpha = (1 - confidence) / 2
    lo = bootstrap_stats[max(0, int(alpha * n_bootstrap))]
    hi = bootstrap_stats[min(n_bootstrap - 1, int((1 - alpha) * n_bootstrap))]
    return (lo, hi)


async def faithfulness_judge(
    query: str, answer: str, retrieved: list[dict]
) -> float | None:
    """LLM-as-judge for faithfulness.
    Returns 1.0 (SUPPORTED), 0.5 (PARTIAL), 0.0 (UNSUPPORTED), None (error).
    """
    chunks_text = "\n---\n".join(c.get("text", "") for c in retrieved[:8])
    prompt = FAITHFULNESS_PROMPT.format(chunks=chunks_text, answer=answer)

    try:
        verdict = await call_llm(
            [{"role": "user", "content": prompt}],
            max_tokens=80,
        )
        verdict_upper = verdict.strip().upper()
        if "SUPPORTED" in verdict_upper and "PARTIAL" not in verdict_upper:
            return 1.0
        elif "PARTIAL" in verdict_upper:
            return 0.5
        elif "UNSUPPORTED" in verdict_upper:
            return 0.0
        return None
    except Exception:
        return None
