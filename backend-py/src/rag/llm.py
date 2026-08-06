from __future__ import annotations

import os
import time
import urllib.parse
from typing import AsyncGenerator

from openai import AsyncOpenAI

from rag.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, config
from rag.logger import log_llm_call, logger

_client: AsyncOpenAI | None = None

_PRIVATE_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _check_local_provider_security() -> None:
    """If LLM_PROVIDER=local, refuse to start when LLM_BASE_URL points to a public domain."""
    if os.getenv("LLM_PROVIDER", "").lower() != "local":
        return
    try:
        host = urllib.parse.urlparse(LLM_BASE_URL).hostname or ""
        is_private = (
            host in _PRIVATE_HOSTS
            or host.startswith("192.168.")
            or host.startswith("10.")
            or host.startswith("172.")
            or host.endswith(".local")
        )
        if not is_private:
            raise SystemExit(
                f"LLM_PROVIDER=local requires LLM_BASE_URL to be a private/loopback "
                f"address. Got '{LLM_BASE_URL}'. Refusing to start."
            )
    except SystemExit:
        raise
    except Exception:
        pass


_check_local_provider_security()


def get_client() -> AsyncOpenAI:
    """Singleton OpenAI-compatible client. Provider is set entirely from env."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY or "sk-none",
            timeout=config.llm.request_timeout_s,
        )
    return _client


async def call_llm(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    request_id: str | None = None,
) -> str:
    """
    Single entry point for all LLM calls.
    Provider-swap rule: ONLY this function may call the LLM.
    All other modules must import and call call_llm().
    """
    _model = model or LLM_MODEL
    _temp = temperature if temperature is not None else config.llm.temperature
    _max = max_tokens or config.llm.max_output_tokens

    client = get_client()
    start = time.monotonic()

    try:
        resp = await client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=_temp,
            max_tokens=_max,
        )
        content = resp.choices[0].message.content or ""
        latency_ms = int((time.monotonic() - start) * 1000)

        log_llm_call(
            {
                "request_id": request_id,
                "model": _model,
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else None,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else None,
                "latency_ms": latency_ms,
            }
        )
        return content

    except Exception as exc:
        logger.error("LLM call failed", model=_model, error=str(exc))
        raise


async def call_llm_stream(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    request_id: str | None = None,
) -> AsyncGenerator[str, None]:
    _model = model or LLM_MODEL
    _temp = temperature if temperature is not None else config.llm.temperature
    _max = max_tokens or config.llm.max_output_tokens

    client = get_client()
    start = time.monotonic()
    prompt_tokens = 0
    completion_tokens = 0

    try:
        stream = await client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=_temp,
            max_tokens=_max,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        latency_ms = int((time.monotonic() - start) * 1000)
        log_llm_call(
            {
                "request_id": request_id,
                "model": _model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
            }
        )
    except Exception as exc:
        logger.error("LLM stream failed", model=_model, error=str(exc))
        raise
