from __future__ import annotations

import re
from dataclasses import dataclass, field

import tiktoken

from rag.config import config
from rag.logger import logger

enc = tiktoken.get_encoding("cl100k_base")

MAX_ATOMIC_TOKENS = 1200  # cap for tables/code blocks — warn if exceeded


@dataclass
class Chunk:
    text: str
    section_path: list[str]
    chunk_index: int
    token_count: int


# ── Token helpers ─────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def decode_tokens(tokens: list[int]) -> str:
    return enc.decode(tokens)


# ── Atomic block detection ────────────────────────────────────────────────────

def split_into_segments(body: str) -> list[tuple[str, bool]]:
    """
    Split a section body into (text, is_atomic) segments.
    is_atomic=True means the segment is a table or fenced code block
    and must not be split further.
    """
    lines = body.split("\n")
    segments: list[tuple[str, bool]] = []
    buf: list[str] = []
    in_code = False
    in_table = False

    for line in lines:
        is_code_fence = line.strip().startswith("```") or line.strip().startswith("~~~")
        is_table_row = line.strip().startswith("|")

        if is_code_fence:
            if in_code:
                buf.append(line)
                segments.append(("\n".join(buf), True))
                buf = []
                in_code = False
            else:
                if buf:
                    segments.append(("\n".join(buf), in_table))
                    buf = []
                buf.append(line)
                in_code = True
            continue

        if in_code:
            buf.append(line)
            continue

        if is_table_row:
            if not in_table:
                if buf:
                    segments.append(("\n".join(buf), False))
                    buf = []
                in_table = True
            buf.append(line)
        else:
            if in_table:
                segments.append(("\n".join(buf), True))
                buf = []
                in_table = False
            buf.append(line)

    if buf:
        segments.append(("\n".join(buf), in_code or in_table))

    return segments


# ── Sliding-window splitter (for non-atomic text) ─────────────────────────────

def token_window_split(text: str, target: int, overlap: int, min_tokens: int) -> list[str]:
    tokens = enc.encode(text)
    if not tokens:
        return []

    result: list[str] = []
    i = 0
    while i < len(tokens):
        end = min(i + target, len(tokens))
        chunk_tokens = tokens[i:end]
        chunk_text = enc.decode(chunk_tokens)
        if len(chunk_tokens) >= min_tokens:
            result.append(chunk_text)
        i += target - overlap

    return result


# ── Section-aware markdown parser ─────────────────────────────────────────────

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def parse_sections(markdown: str) -> list[tuple[list[str], str]]:
    """
    Parse markdown into (section_path, body) tuples.
    section_path = list of heading strings leading to this section.
    body = the text content under that heading.
    """
    lines = markdown.split("\n")
    sections: list[tuple[list[str], str]] = []

    current_path: list[str] = []
    current_level: list[int] = []
    current_body: list[str] = []

    def flush():
        if current_body:
            sections.append((list(current_path), "\n".join(current_body).strip()))
        current_body.clear()

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            depth = len(m.group(1))
            title = m.group(2).strip()

            # Pop stack to current depth
            while current_level and current_level[-1] >= depth:
                current_level.pop()
                current_path.pop()

            current_level.append(depth)
            current_path.append(title)
        else:
            current_body.append(line)

    flush()

    # If there were no headings, return full document as one section
    if not sections:
        sections = [([], markdown.strip())]

    return sections


# ── Main chunker ──────────────────────────────────────────────────────────────

def chunk_markdown(markdown: str) -> list[Chunk]:
    target = config.chunk.target_tokens
    overlap = config.chunk.overlap_tokens
    min_tok = config.chunk.min_tokens

    sections = parse_sections(markdown)
    all_chunks: list[Chunk] = []
    chunk_index = 0

    for section_path, body in sections:
        if not body.strip():
            continue

        segments = split_into_segments(body)

        # Merge non-atomic segments into windows; flush atomics individually
        pending: list[str] = []

        for seg_text, is_atomic in segments:
            if not seg_text.strip():
                continue

            tok_count = count_tokens(seg_text)

            if is_atomic:
                # First flush any pending non-atomic text
                if pending:
                    joined = "\n".join(pending)
                    for window in token_window_split(joined, target, overlap, min_tok):
                        all_chunks.append(
                            Chunk(
                                text=window,
                                section_path=section_path,
                                chunk_index=chunk_index,
                                token_count=count_tokens(window),
                            )
                        )
                        chunk_index += 1
                    pending = []

                # Atomic block — keep whole, warn if over cap
                if tok_count > MAX_ATOMIC_TOKENS:
                    logger.warning(
                        "Atomic block exceeds token cap",
                        tokens=tok_count,
                        cap=MAX_ATOMIC_TOKENS,
                        section=section_path,
                    )

                all_chunks.append(
                    Chunk(
                        text=seg_text,
                        section_path=section_path,
                        chunk_index=chunk_index,
                        token_count=tok_count,
                    )
                )
                chunk_index += 1
            else:
                pending.append(seg_text)

        # Flush remaining pending
        if pending:
            joined = "\n".join(pending)
            for window in token_window_split(joined, target, overlap, min_tok):
                tc = count_tokens(window)
                # Keep short sections that are standalone (definitions, headers+body)
                if tc >= min_tok or (len(sections) == 1 and section_path):
                    all_chunks.append(
                        Chunk(
                            text=window,
                            section_path=section_path,
                            chunk_index=chunk_index,
                            token_count=tc,
                        )
                    )
                    chunk_index += 1

    return all_chunks
