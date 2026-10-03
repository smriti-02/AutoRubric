"""Retrieval Evaluation Script: Evaluate recall@k and precision on labelled benchmark."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from autorubric.contracts import Proposition, BBox, Rubric, Candidate
from autorubric.retrieval.matcher import match


RUBRICS = {
    "r-bio": Rubric(
        id="r-bio",
        title="Plant Cell Structure & Photosynthesis",
        max_score=6.0,
        credit_map={"FULL_CREDIT": 1.0, "PARTIAL_CREDIT": 0.5, "NO_CREDIT": 0.0, "MISCONCEPTION": 0.0},
        criteria=[
            {"id": "c1", "description": "Mentions that chloroplasts contain chlorophyll to absorb light energy.", "weight": 2.0, "depends_on": []},
            {"id": "c2", "description": "Identifies water photolysis releasing oxygen as a product.", "weight": 2.0, "depends_on": []},
            {"id": "c3", "description": "Explains that carbon dioxide is fixed to synthesize glucose.", "weight": 2.0, "depends_on": []},
        ],
    ),
    "r-cs": Rubric(
        id="r-cs",
        title="Processes and Threads Architecture",
        max_score=6.0,
        credit_map={"FULL_CREDIT": 1.0, "PARTIAL_CREDIT": 0.5, "NO_CREDIT": 0.0, "MISCONCEPTION": 0.0},
        criteria=[
            {"id": "cs1", "description": "Process has an independent and isolated virtual address space.", "weight": 2.0, "depends_on": []},
            {"id": "cs2", "description": "Peer threads within the same process share common memory heap and code.", "weight": 2.0, "depends_on": []},
            {"id": "cs3", "description": "Each individual thread maintains its own call stack and CPU register state.", "weight": 2.0, "depends_on": []},
        ],
    ),
}


def load_dataset() -> List[Dict[str, Any]]:
    path = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "retrieval" / "eval_dataset.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_set(dataset: List[Dict[str, Any]], threshold: float, top_k: int = 3) -> Dict[str, Any]:
    total_positives = sum(1 for item in dataset if item["criterion_id"] is not None)
    total_negatives = sum(1 for item in dataset if item["criterion_id"] is None)

    correct_at_1 = 0
    correct_at_k = 0
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    for item in dataset:
        rubric = RUBRICS[item["rubric_id"]]
        expected_crit = item["criterion_id"]

        prop = Proposition(
            id=item["id"],
            doc_id="eval_doc",
            text=item["proposition"],
            token_ids=[f"t_{item['id']}"],
            page=1,
            bboxes=[BBox(x=10.0, y=20.0, w=100.0, h=10.0, page=1)],
            from_hidden_text=False,
        )

        candidates = match([prop], rubric, top_k=top_k, threshold=threshold)
        retrieved_ids = [c.criterion_id for c in candidates]

        if expected_crit is not None:
            if retrieved_ids:
                if retrieved_ids[0] == expected_crit:
                    correct_at_1 += 1
                if expected_crit in retrieved_ids:
                    correct_at_k += 1
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                false_negatives += 1
        else:
            if retrieved_ids:
                false_positives += 1
            else:
                true_negatives += 1

    recall_1 = correct_at_1 / total_positives if total_positives else 0.0
    recall_k = correct_at_k / total_positives if total_positives else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) else 0.0

    return {
        "total_pairs": len(dataset),
        "total_positives": total_positives,
        "total_negatives": total_negatives,
        "correct_at_1": correct_at_1,
        "correct_at_k": correct_at_k,
        "recall_at_1": round(recall_1, 4),
        f"recall_at_{top_k}": round(recall_k, 4),
        "precision": round(precision, 4),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
    }


def run_benchmark():
    dataset = load_dataset()
    # Split into 50% tuning set and 50% held-out test set
    tuning_set = dataset[:20]
    held_out_set = dataset[20:]

    print(f"Loaded {len(dataset)} total evaluation pairs.")
    print(f"Tuning set: {len(tuning_set)} pairs | Held-out test set: {len(held_out_set)} pairs\n")

    # Threshold sweep on tuning set
    best_thresh = 0.15
    best_f1 = -1.0

    print("--- Tuning Set Parameter Search ---")
    for thresh in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        res = evaluate_set(tuning_set, threshold=thresh, top_k=3)
        p = res["precision"]
        r = res["recall_at_3"]
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        print(f"Thresh: {thresh:.2f} -> Recall@1: {res['recall_at_1']} | Recall@3: {res['recall_at_3']} | Precision: {res['precision']} | F1: {f1:.4f}")
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh

    print(f"\nOptimal threshold selected: {best_thresh:.2f} (F1: {best_f1:.4f})\n")

    # Evaluate on held-out test set with chosen threshold
    test_res = evaluate_set(held_out_set, threshold=best_thresh, top_k=3)
    print("--- Held-out Test Set Results ---")
    for k, v in test_res.items():
        print(f"  {k}: {v}")

    # Full set results
    full_res = evaluate_set(dataset, threshold=best_thresh, top_k=3)
    print("\n--- Complete Benchmark Results (All 40 Pairs) ---")
    for k, v in full_res.items():
        print(f"  {k}: {v}")

    return {
        "best_threshold": best_thresh,
        "tuning": evaluate_set(tuning_set, threshold=best_thresh, top_k=3),
        "held_out": test_res,
        "full": full_res,
    }


if __name__ == "__main__":
    run_benchmark()
