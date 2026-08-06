"""Unit tests for retrieve/hybrid.py — tests the pure _rrf_merge function."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.retrieve.hybrid import _rrf_merge


def _doc(id_: str, text: str = "x") -> dict:
    return {"id": id_, "doc_id": "d", "source": "f.txt", "text": text}


def test_item_in_both_lists_ranks_highest():
    dense = [_doc("a"), _doc("b"), _doc("c")]
    sparse = [_doc("b"), _doc("d"), _doc("e")]
    merged = _rrf_merge(dense, sparse, k=60, top_n=10)
    assert merged[0]["id"] == "b", "Item in both lists should rank first"


def test_merged_is_union_of_inputs():
    dense = [_doc("a"), _doc("b")]
    sparse = [_doc("c"), _doc("d")]
    merged = _rrf_merge(dense, sparse, k=60, top_n=10)
    assert {m["id"] for m in merged} == {"a", "b", "c", "d"}


def test_top_n_limits_output():
    dense = [_doc(str(i)) for i in range(10)]
    sparse = [_doc(str(i)) for i in range(5, 15)]
    merged = _rrf_merge(dense, sparse, k=60, top_n=5)
    assert len(merged) == 5


def test_empty_sparse_returns_dense():
    dense = [_doc("a"), _doc("b"), _doc("c")]
    merged = _rrf_merge(dense, [], k=60, top_n=10)
    assert [m["id"] for m in merged] == ["a", "b", "c"]


def test_empty_dense_returns_sparse():
    sparse = [_doc("x"), _doc("y")]
    merged = _rrf_merge([], sparse, k=60, top_n=10)
    assert [m["id"] for m in merged] == ["x", "y"]


def test_both_empty():
    assert _rrf_merge([], [], k=60, top_n=10) == []


def test_score_rrf_present_and_positive():
    dense = [_doc("a"), _doc("b")]
    sparse = [_doc("b"), _doc("c")]
    merged = _rrf_merge(dense, sparse, k=60, top_n=10)
    for item in merged:
        assert "score_rrf" in item
        assert item["score_rrf"] > 0


def test_higher_rank_means_higher_score():
    dense = [_doc("top"), _doc("bottom")]
    merged = _rrf_merge(dense, [], k=60, top_n=10)
    assert merged[0]["score_rrf"] > merged[1]["score_rrf"]
