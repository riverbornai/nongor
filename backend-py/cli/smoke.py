#!/usr/bin/env python3
"""Smoke test: python -m cli.smoke [text]
Verifies LLM provider is reachable and returns a completion."""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "src")

from rag.config import LLM_BASE_URL, LLM_MODEL
from rag.llm import call_llm


async def main() -> None:
    text = " ".join(sys.argv[1:]) or "hello"
    print(f"Smoke testing LLM provider...")
    print(f"  base_url : {LLM_BASE_URL}")
    print(f"  model    : {LLM_MODEL}")
    response = await call_llm(
        [{"role": "user", "content": text}],
        max_tokens=5,
    )
    print(f"  response : {repr(response)}")
    print("Smoke test passed.")


if __name__ == "__main__":
    asyncio.run(main())
