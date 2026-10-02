"""Unit tests for ingest/chunk.py — pure logic, no I/O."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from rag.ingest.chunk import (
    chunk_markdown,
    count_tokens,
    parse_sections,
    split_into_segments,
    token_window_split,
)


# ── parse_sections ─────────────────────────────────────────────────────────────

def test_parse_sections_single_heading():
    md = "# Title\n\nBody text here."
    sections = parse_sections(md)
    assert len(sections) == 1
    assert sections[0][0] == ["Title"]
    assert "Body text" in sections[0][1]


def test_parse_sections_nested_headings():
    md = "# Chapter 1\n\nIntro.\n\n## Section 1.1\n\nContent.\n\n## Section 1.2\n\nMore."
    sections = parse_sections(md)
    assert len(sections) == 3
    assert sections[1][0] == ["Chapter 1", "Section 1.1"]
    assert sections[2][0] == ["Chapter 1", "Section 1.2"]


def test_parse_sections_no_headings():
    md = "Just some plain text with no headings at all."
    sections = parse_sections(md)
    assert len(sections) == 1
    assert sections[0][0] == []
    assert "plain text" in sections[0][1]


def test_parse_sections_empty():
    sections = parse_sections("")
    assert sections == [([], "")]


# ── split_into_segments ────────────────────────────────────────────────────────

def test_code_block_is_atomic():
    body = "Intro text.\n\n```python\nprint('hello')\nx = 1\n```\n\nOutro text."
    segments = split_into_segments(body)
    atomic = [s for s, is_a in segments if is_a]
    assert len(atomic) == 1
    assert "print('hello')" in atomic[0]
    assert "```python" in atomic[0]


def test_table_is_atomic():
    body = "Before.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nAfter."
    segments = split_into_segments(body)
    atomic = [s for s, is_a in segments if is_a]
    assert len(atomic) == 1
    assert "| A | B |" in atomic[0]


def test_plain_text_not_atomic():
    body = "Just regular text.\nNo special blocks."
    segments = split_into_segments(body)
    assert all(not is_a for _, is_a in segments)


# ── token_window_split ─────────────────────────────────────────────────────────

def test_window_split_respects_target_size():
    words = " ".join(["word"] * 300)
    target = 80
    overlap = 10
    windows = token_window_split(words, target, overlap, min_tokens=5)
    for w in windows:
        assert count_tokens(w) <= target + 5  # small tolerance for tokenizer boundaries


def test_window_split_overlap_creates_more_chunks():
    words = " ".join(["word"] * 200)
    no_overlap = token_window_split(words, 50, 0, min_tokens=5)
    with_overlap = token_window_split(words, 50, 20, min_tokens=5)
    assert len(with_overlap) > len(no_overlap)


def test_window_split_empty():
    assert token_window_split("", 50, 10, min_tokens=5) == []


# ── chunk_markdown end-to-end ──────────────────────────────────────────────────

def test_chunk_markdown_preserves_section_path():
    # Use 150 words per section to exceed min_tokens=100
    md = (
        "# Chapter 1\n\n" + " ".join(["word"] * 150) + "\n\n"
        "## Section 1.1\n\n" + " ".join(["text"] * 150)
    )
    chunks = chunk_markdown(md)
    paths = [c.section_path for c in chunks]
    assert any("Chapter 1" in p for p in paths), "Expected a chunk under 'Chapter 1'"
    assert any("Section 1.1" in p for p in paths), "Expected a chunk under 'Section 1.1'"


def test_chunk_markdown_code_block_not_split():
    code_lines = "\n".join(f"    x_{i} = {i}" for i in range(80))
    md = f"# Section\n\n```python\n{code_lines}\n```\n"
    chunks = chunk_markdown(md)
    code_chunks = [c for c in chunks if "```python" in c.text]
    assert len(code_chunks) == 1, "Code block must appear in exactly one chunk"


def test_chunk_markdown_chunk_indices_sequential():
    md = "# A\n\n" + " ".join(["w"] * 500)
    chunks = chunk_markdown(md)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
