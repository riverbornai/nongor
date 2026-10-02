#!/usr/bin/env python
"""Entry point: uvicorn rag.api.main:app"""
import os
import sys
sys.path.insert(0, "src")

import uvicorn
from rag.config import config

if __name__ == "__main__":
    is_dev = os.getenv("ENV", "development") == "development"
    uvicorn.run(
        "rag.api.main:app",
        host=config.api.host,
        port=int(os.getenv("PORT", config.api.port)),
        reload=is_dev,
        reload_dirs=["src"] if is_dev else None,
        log_level="info",
    )
