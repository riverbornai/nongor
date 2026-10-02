#!/usr/bin/env python3
"""
Evaluation harness.
Usage: python -m eval.run
Reads eval/dataset.jsonl, runs each query through the answer pipeline,
computes Recall@5, Recall@10, MRR, citation validity, faithfulness.
Writes results to eval/results/<timestamp>.json and flags regressions vs last run.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval.metrics import (
    bootstrap_ci,
    citation_validity,
    faithfulness_judge,
    mrr,
    recall_at_k,
)
from rag.generate.answer import answer_query

DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

REGRESSION_THRESHOLD = 0.03  # flag if metric drops ≥ 3% relative


def _load_last_results() -> dict | None:
    """Return aggregate metrics from the most recent previous run, if any."""
    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text()).get("aggregate")
    except Exception:
        return None


def _check_regressions(current: dict, previous: dict) -> list[str]:
    regressions = []
    for key in ("recall_5", "recall_10", "faithfulness", "citation_validity"):
        prev_val = previous.get(key, 0.0)
        curr_val = current.get(key, 0.0)
        if prev_val > 0 and (prev_val - curr_val) / prev_val >= REGRESSION_THRESHOLD:
            delta_pct = (curr_val - prev_val) / prev_val * 100
            regressions.append(
                f"  {key}: {curr_val:.3f} vs {prev_val:.3f} ({delta_pct:+.1f}%)"
            )
    return regressions


async def run_eval() -> None:
    if not DATASET_PATH.exists():
        print(f"ERROR: {DATASET_PATH} not found. Create the eval dataset first.")
        sys.exit(1)

    with open(DATASET_PATH) as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    print(f"Running eval on {len(dataset)} questions...\n")

    prev_agg = _load_last_results()

    results = []
    per_q: dict[str, list[float]] = {
        "recall_5": [], "recall_10": [], "mrr": [],
        "citation_validity": [], "faithfulness": [],
    }

    for item in dataset:
        qid = item["id"]
        query = item["query"]
        expected_ids = set(item.get("expected_chunk_ids", []))
        must_contain = item.get("must_contain", [])
        must_not_contain = item.get("must_not_contain", [])

        try:
            resp = await answer_query(query, request_id=qid)
        except Exception as exc:
            print(f"[{qid}] ERROR: {exc}")
            results.append({"id": qid, "error": str(exc)})
            continue

        retrieved_ids = [c["id"] for c in resp.retrieved]
        r5 = recall_at_k(retrieved_ids, expected_ids, k=5)
        r10 = recall_at_k(retrieved_ids, expected_ids, k=10)
        mrr_score = mrr(retrieved_ids, expected_ids)
        cit_valid = citation_validity(resp)
        must_pass = all(m in resp.answer for m in must_contain)
        must_not_pass = all(m not in resp.answer for m in must_not_contain)
        faith = await faithfulness_judge(query, resp.answer, resp.retrieved)

        per_q["recall_5"].append(r5)
        per_q["recall_10"].append(r10)
        per_q["mrr"].append(mrr_score)
        per_q["citation_validity"].append(cit_valid)
        if faith is not None:
            per_q["faithfulness"].append(faith)

        row = {
            "id": qid, "query": query,
            "recall_5": r5, "recall_10": r10, "mrr": mrr_score,
            "citation_validity": cit_valid,
            "must_contain_pass": must_pass,
            "must_not_contain_pass": must_not_pass,
            "faithfulness": faith,
            "timings_ms": resp.timings_ms,
        }
        results.append(row)

        status = "✓" if r5 >= 0.5 else "!"
        print(f"[{status}] [{qid}] R@5={r5:.2f} R@10={r10:.2f} MRR={mrr_score:.2f} Faith={faith}")

    valid = [r for r in results if "error" not in r]
    if not valid:
        print("No valid results.")
        return

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    agg = {
        "recall_5": _mean(per_q["recall_5"]),
        "recall_10": _mean(per_q["recall_10"]),
        "mrr": _mean(per_q["mrr"]),
        "citation_validity": _mean(per_q["citation_validity"]),
        "faithfulness": _mean(per_q["faithfulness"]),
        "n": len(valid),
    }

    # Bootstrap 95% CIs
    cis = {k: bootstrap_ci(per_q[k]) for k in ("recall_5", "recall_10", "faithfulness", "citation_validity")}

    print(f"\n{'='*65}")
    print(f"  EVAL RESULTS  (n={agg['n']})")
    print(f"{'='*65}")
    print(f"  Recall@5          : {agg['recall_5']:.3f} ± {(cis['recall_5'][1]-cis['recall_5'][0])/2:.3f}  (target ≥ 0.85)")
    print(f"  Recall@10         : {agg['recall_10']:.3f} ± {(cis['recall_10'][1]-cis['recall_10'][0])/2:.3f}  (target ≥ 0.92)")
    print(f"  MRR               : {agg['mrr']:.3f}")
    print(f"  Citation validity : {agg['citation_validity']:.3f} ± {(cis['citation_validity'][1]-cis['citation_validity'][0])/2:.3f}  (target ≥ 0.95)")
    print(f"  Faithfulness      : {agg['faithfulness']:.3f} ± {(cis['faithfulness'][1]-cis['faithfulness'][0])/2:.3f}  (target ≥ 0.90)")
    print(f"{'='*65}\n")

    # Regression check vs last run
    if prev_agg:
        regressions = _check_regressions(agg, prev_agg)
        if regressions:
            print("REGRESSIONS vs last run (≥3% relative drop):")
            for r in regressions:
                print(r)
            print()
        else:
            print("No regressions vs last run.\n")
    else:
        print("No previous run found — this is the baseline.\n")

    # Write results
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{ts}.json"
    with open(out_path, "w") as f:
        json.dump({"aggregate": agg, "confidence_intervals": {k: list(v) for k, v in cis.items()}, "per_question": results, "timestamp": ts}, f, indent=2)
    print(f"Results written to {out_path}")

    # Check targets
    failures = []
    if agg["recall_5"] < 0.85:
        failures.append(f"Recall@5 {agg['recall_5']:.3f} < 0.85")
    if agg["recall_10"] < 0.92:
        failures.append(f"Recall@10 {agg['recall_10']:.3f} < 0.92")
    if agg["faithfulness"] < 0.90:
        failures.append(f"Faithfulness {agg['faithfulness']:.3f} < 0.90")
    if agg["citation_validity"] < 0.95:
        failures.append(f"Citation validity {agg['citation_validity']:.3f} < 0.95")

    if failures:
        print("TARGETS NOT MET:")
        for line in failures:
            print(f"   * {line}")
        sys.exit(1)
    else:
        print("All targets met!")


if __name__ == "__main__":
    asyncio.run(run_eval())
