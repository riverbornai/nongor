#!/usr/bin/env python3
"""CLI: python -m cli.query "your question here" """
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "src")

from rag.generate.answer import answer_query


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m cli.query "your question"', file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = await answer_query(query, request_id="cli")

    print(f"\n{'='*60}")
    print(f"ANSWER:\n{result.answer}")
    print(f"\nCITATIONS ({len(result.citations)}):")
    for c in result.citations:
        print(f"  [{c.id[:8]}…] {c.source} — {c.text_snippet[:80]}…")
    if result.invalid_citation_ids:
        print(f"\nINVALID CITATIONS: {result.invalid_citation_ids}")
    print(f"\nTIMINGS: {result.timings_ms}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
