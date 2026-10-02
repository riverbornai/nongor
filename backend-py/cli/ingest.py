#!/usr/bin/env python3
"""CLI: python -m cli.ingest <path|url> [--no-context]"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "src")

from rag.ingest.pipeline import ingest_source


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m cli.ingest <path|url> [--no-context]", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    use_prefix = "--no-context" not in sys.argv

    result = await ingest_source(source, use_prefix=use_prefix)
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
