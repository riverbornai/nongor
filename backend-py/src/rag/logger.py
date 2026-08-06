from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import structlog

from rag.config import LOG_LEVEL, ROOT

# ── file paths ────────────────────────────────────────────────────────────────
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LLM_CALLS_PATH = DATA_DIR / "llm_calls.jsonl"

# ── stdlib logging → structlog bridge ─────────────────────────────────────────
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def log_llm_call(entry: dict) -> None:
    """Append a single LLM call record to llm_calls.jsonl for cost analysis."""
    import datetime

    record = {**entry, "ts": datetime.datetime.utcnow().isoformat() + "Z"}
    with open(LLM_CALLS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ── builtins.print patch for server steps ──────────────────────────────────────
import builtins
from contextvars import ContextVar
from typing import Callable

step_callback_var: ContextVar[Callable[[str], None] | None] = ContextVar("step_callback", default=None)

_original_print = builtins.print

def _custom_print(*args, **kwargs):
    _original_print(*args, **kwargs)
    callback = step_callback_var.get()
    if callback is not None:
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)
        if "[SERVER STEP]" in message:
            step_text = message.replace("[SERVER STEP]", "").strip()
            if step_text:
                callback(step_text)

builtins.print = _custom_print

