"""ML Evaluator Classifier Module.

Supports:
- Backends: 'mock' (deterministic lexical heuristic), 'cpu', 'gpu' (PyTorch/Transformers).
- Lazy model loading once per process.
- Strict error handling with explicit fallback control (EVALUATOR_ALLOW_MOCK_FALLBACK).
- Deterministic IDs and calibrated confidences.
"""

from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from autorubric.contracts import Label, Classification, Candidate, EvalPair

logger = logging.getLogger(__name__)

_LOADED_MODEL = None
_LOADED_TOKENIZER = None
_LABEL_MAP = None


def get_evaluator_backend() -> str:
    return os.environ.get("EVALUATOR_BACKEND", "mock").lower()


def model_info() -> Dict[str, Any]:
    backend = get_evaluator_backend()
    model_path = os.environ.get("EVALUATOR_MODEL_PATH", str(Path(__file__).resolve().parents[4] / "ml" / "checkpoint"))
    has_weights = os.path.isdir(model_path) and any(os.scandir(model_path))
    return {
        "backend": backend,
        "model_path": model_path,
        "weights_present": has_weights,
        "version": "1.0.0",
        "taxonomy": ["FULL_CREDIT", "PARTIAL_CREDIT", "MISCONCEPTION", "NO_CREDIT"],
    }


def _classify_mock(pairs: List[Union[EvalPair, Candidate]]) -> List[Classification]:
    """Deterministic lexical overlap and negation heuristic running in pure Python."""
    results: List[Classification] = []

    negation_words = {"not", "never", "cannot", "opposite", "no", "fails", "instead", "contradicts"}
    misconception_stems = [
        ("mitochondri", "chloroplast"),
        ("chloroplast", "mitochondri"),
        ("nucleus", "chloroplast"),
        ("glucose", "carbon dioxide"),
        ("thread", "process"),
    ]

    for p in pairs:
        prop_text = getattr(p, "proposition_text", "") or ""
        crit_text = getattr(p, "criterion_text", "") or ""
        prop_id = p.prop_id
        crit_id = p.criterion_id

        p_words = set(re.findall(r"\b\w+\b", prop_text.lower()))
        c_words = set(re.findall(r"\b\w+\b", crit_text.lower()))

        # If text is empty (e.g. basic Candidate without text fields), use similarity score
        if not p_words or not c_words:
            sim = getattr(p, "similarity", 0.5)
            if sim >= 0.75:
                lbl = Label.FULL_CREDIT
                conf = round(min(0.95, sim + 0.1), 4)
            elif sim >= 0.40:
                lbl = Label.PARTIAL_CREDIT
                conf = round(sim, 4)
            else:
                lbl = Label.NO_CREDIT
                conf = round(1.0 - sim, 4)
        else:
            # Check for contradiction / misconception cues
            has_negation = bool(p_words.intersection(negation_words))
            has_sub_swap = any(
                any(w.startswith(s1) for w in p_words) and any(w.startswith(s2) for w in c_words)
                for s1, s2 in misconception_stems
            )

            intersection = p_words.intersection(c_words)
            overlap_ratio = len(intersection) / max(len(c_words), 1)

            if has_sub_swap or (has_negation and overlap_ratio > 0.3):
                lbl = Label.MISCONCEPTION
                conf = 0.88
            elif overlap_ratio >= 0.40:
                lbl = Label.FULL_CREDIT
                conf = round(min(0.98, 0.70 + overlap_ratio * 0.3), 4)
            elif overlap_ratio >= 0.20:
                lbl = Label.PARTIAL_CREDIT
                conf = round(0.60 + overlap_ratio * 0.4, 4)
            else:
                lbl = Label.NO_CREDIT
                conf = round(0.75 + (1.0 - overlap_ratio) * 0.15, 4)

        results.append(
            Classification(
                id=f"cls_{prop_id}_{crit_id}",
                prop_id=prop_id,
                criterion_id=crit_id,
                label=lbl,
                confidence=conf,
            )
        )

    return results


def _load_transformer_model(device: str):
    global _LOADED_MODEL, _LOADED_TOKENIZER, _LABEL_MAP
    if _LOADED_MODEL is not None:
        return _LOADED_MODEL, _LOADED_TOKENIZER, _LABEL_MAP

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    model_dir = os.environ.get("EVALUATOR_MODEL_PATH", str(Path(__file__).resolve().parents[4] / "ml" / "checkpoint"))

    if not os.path.isdir(model_dir) or not (Path(model_dir) / "config.json").exists():
        allow_fallback = os.environ.get("EVALUATOR_ALLOW_MOCK_FALLBACK", "false").lower() == "true"
        if allow_fallback:
            logger.warning(f"Model checkpoint not found at {model_dir}. Falling back to mock backend.")
            return None, None, None
        raise FileNotFoundError(
            f"Evaluator weights not found at {model_dir}. Set EVALUATOR_BACKEND=mock or provide model weights."
        )

    label_map_file = Path(model_dir) / "label_map.json"
    if label_map_file.exists():
        with open(label_map_file, "r", encoding="utf-8") as f:
            _LABEL_MAP = json.load(f).get("id2label", {})
            _LABEL_MAP = {int(k): v for k, v in _LABEL_MAP.items()}
    else:
        _LABEL_MAP = {0: "FULL_CREDIT", 1: "PARTIAL_CREDIT", 2: "MISCONCEPTION", 3: "NO_CREDIT"}

    _LOADED_TOKENIZER = AutoTokenizer.from_pretrained(model_dir)
    _LOADED_MODEL = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device)
    _LOADED_MODEL.eval()
    return _LOADED_MODEL, _LOADED_TOKENIZER, _LABEL_MAP


def _classify_torch(pairs: List[Union[EvalPair, Candidate]], device: str = "cpu") -> List[Classification]:
    model, tokenizer, id2label = _load_transformer_model(device)
    if model is None:
        return _classify_mock(pairs)

    import torch

    batch_size = int(os.environ.get("EVALUATOR_BATCH_SIZE", "16"))
    temperature = float(os.environ.get("EVALUATOR_TEMPERATURE", "1.0"))
    results: List[Classification] = []

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i : i + batch_size]
        texts_a = [getattr(p, "criterion_text", "") or "" for p in batch]
        texts_b = [getattr(p, "proposition_text", "") or "" for p in batch]

        encodings = tokenizer(
            texts_a,
            texts_b,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            logits = model(**encodings).logits
            scaled_logits = logits / max(temperature, 1e-4)
            probs = torch.softmax(scaled_logits, dim=-1)
            confidences, preds = torch.max(probs, dim=-1)

        for p, pred_idx, conf in zip(batch, preds.cpu().tolist(), confidences.cpu().tolist()):
            lbl_str = id2label.get(pred_idx, "NO_CREDIT")
            results.append(
                Classification(
                    id=f"cls_{p.prop_id}_{p.criterion_id}",
                    prop_id=p.prop_id,
                    criterion_id=p.criterion_id,
                    label=Label(lbl_str),
                    confidence=round(float(conf), 4),
                )
            )

    return results


def classify(pairs: List[Union[EvalPair, Candidate]]) -> List[Classification]:
    """Public classify function for evaluating proposition/criterion candidate pairs.

    Guarantees:
    - Same ordering as input pairs.
    - Deterministic IDs.
    - Confidence score between 0.0 and 1.0.
    - Empty input returns empty list.
    """
    if not pairs:
        return []

    backend = get_evaluator_backend()
    if backend == "mock":
        return _classify_mock(pairs)
    elif backend in ("cpu", "gpu"):
        device = "cuda" if backend == "gpu" else "cpu"
        try:
            return _classify_torch(pairs, device=device)
        except FileNotFoundError:
            if os.environ.get("EVALUATOR_ALLOW_MOCK_FALLBACK", "false").lower() == "true":
                return _classify_mock(pairs)
            raise
    else:
        raise ValueError(f"Unknown evaluator backend: {backend!r}. Choose 'mock', 'cpu', or 'gpu'.")
