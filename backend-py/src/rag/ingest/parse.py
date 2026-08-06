from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from rag.logger import logger
from rag.llm import call_llm

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".md", ".txt"}

# Global executor for blocking Docling calls
_executor = ThreadPoolExecutor(max_workers=4)
_docling_converter = None

def get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter
        print("\n[SERVER STEP] Loading Docling DocumentConverter (this takes time and may download PyTorch layout/OCR model weights on first run)...", flush=True)
        _docling_converter = DocumentConverter()
        print("[SERVER STEP] Docling DocumentConverter successfully loaded!\n", flush=True)
    return _docling_converter


@dataclass
class ParsedDocument:
    source: str
    source_type: str  # "file" | "url"
    title: str
    markdown: str
    sha256: str  # SHA-256 of normalized markdown (for idempotency)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ── Docling-based parsing ─────────────────────────────────────────────────────

async def _docling_parse(content: bytes | Path, filename: str) -> str:
    """Use Docling to extract clean markdown from a file or buffer."""
    loop = asyncio.get_running_loop()
    
    def _convert():
        print(f"[SERVER STEP] Starting Docling conversion/parsing for: {filename}...", flush=True)
        converter = get_docling_converter()
        # Docling can handle Path objects or DocumentStreams
        if isinstance(content, bytes):
            from docling.datamodel.base_models import DocumentStream
            import io
            stream = DocumentStream(name=filename, stream=io.BytesIO(content))
            result = converter.convert(stream)
        else:
            result = converter.convert(content)
        
        print(f"[SERVER STEP] Docling converted document to markdown successfully!", flush=True)
        return result.document.export_to_markdown()

    logger.info("Starting Docling extraction", filename=filename)
    try:
        markdown = await loop.run_in_executor(_executor, _convert)
        return markdown
    except Exception as exc:
        logger.error("Docling extraction failed", filename=filename, error=str(exc))
        raise


# ── LLM-based parsing (Fallback/Text-only) ────────────────────────────────────

async def _llm_cleanup(text: str) -> str:
    """Optional: Use LLM to clean up noisy text/markdown."""
    messages = [
        {
            "role": "system",
            "content": "Clean up the following markdown. Fix formatting, remove noise, but preserve ALL content."
        },
        {"role": "user", "content": text}
    ]
    return await call_llm(messages)


# ── File parsing ──────────────────────────────────────────────────────────────

async def parse_file(path: str) -> ParsedDocument:
    """Parse a local file to markdown."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {SUPPORTED_EXTENSIONS}")

    title = p.name

    if ext in {".pdf", ".docx", ".pptx", ".html"}:
        markdown = await _docling_parse(p, title)
    elif ext in {".md", ".txt"}:
        markdown = p.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unhandled extension: {ext}")

    markdown = markdown.strip()
    logger.info("Parsed file", path=path, chars=len(markdown))
    return ParsedDocument(
        source=path,
        source_type="file",
        title=title,
        markdown=markdown,
        sha256=_sha256(markdown),
    )


# ── URL parsing ───────────────────────────────────────────────────────────────

async def parse_url(url: str) -> ParsedDocument:
    """
    Fetch a URL and extract clean text using trafilatura/playwright.
    """
    markdown = _trafilatura_fetch(url)

    if not markdown or len(markdown.strip()) < 100:
        logger.warning("trafilatura returned thin content, trying Playwright", url=url)
        markdown = _playwright_fetch(url)

    if not markdown:
        raise ValueError(f"Failed to extract content from URL: {url}")

    # Derive title from first line or URL
    first_line = markdown.split("\n")[0].lstrip("# ").strip()
    title = first_line[:120] if first_line else url

    markdown = markdown.strip()
    logger.info("Parsed URL", url=url, chars=len(markdown))
    return ParsedDocument(
        source=url,
        source_type="url",
        title=title,
        markdown=markdown,
        sha256=_sha256(markdown),
    )


def _trafilatura_fetch(url: str) -> str | None:
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_tables=True,
        include_links=False,
    )


def _playwright_fetch(url: str) -> str | None:
    """Headless Chromium fallback for JS-rendered pages."""
    try:
        import trafilatura
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)
            html = page.content()
            browser.close()

        return trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=True,
        )
    except Exception as exc:
        logger.warning("Playwright fallback failed", url=url, error=str(exc))
        return None


# ── Buffer parsing (for file uploads) ────────────────────────────────────────

async def parse_buffer(content: bytes, filename: str, content_type: str) -> ParsedDocument:
    """Parse an in-memory file buffer (from multipart upload)."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'")

    if ext in {".md", ".txt"}:
        markdown = content.decode("utf-8")
    else:
        # Use Docling for complex types
        markdown = await _docling_parse(content, filename)

    return ParsedDocument(
        source=filename,
        source_type="file",
        title=filename,
        markdown=markdown,
        sha256=_sha256(markdown),
    )


# ── Unified entry point ───────────────────────────────────────────────────────

async def parse_source(source: str) -> ParsedDocument:
    """Route to file or URL parser based on source string."""
    if source.startswith("http://") or source.startswith("https://"):
        return await parse_url(source)
    return await parse_file(source)
