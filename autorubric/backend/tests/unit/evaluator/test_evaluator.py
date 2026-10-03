import os
import pytest
from autorubric.contracts import Label, Classification, Candidate, EvalPair
from autorubric.evaluator.classifier import classify, model_info


def test_classify_empty_input():
    assert classify([]) == []


def test_classify_ordering_and_deterministic_ids():
    pairs = [
        EvalPair(prop_id="p1", criterion_id="c1", proposition_text="Plant cell chloroplasts absorb sunlight.", criterion_text="Chloroplasts absorb sunlight for photosynthesis."),
        EvalPair(prop_id="p2", criterion_id="c2", proposition_text="Water is split during photolysis.", criterion_text="Water photolysis releases oxygen."),
        EvalPair(prop_id="p3", criterion_id="c1", proposition_text="Mitochondria perform aerobic cellular respiration.", criterion_text="Chloroplasts absorb sunlight for photosynthesis."),
    ]
    results = classify(pairs)
    assert len(results) == 3
    assert results[0].id == "cls_p1_c1"
    assert results[1].id == "cls_p2_c2"
    assert results[2].id == "cls_p3_c1"
    assert results[0].prop_id == "p1"
    assert results[1].prop_id == "p2"
    assert results[2].prop_id == "p3"


def test_classify_mock_credit_labels():
    # 1. Full credit match
    p_full = EvalPair(
        prop_id="p_full",
        criterion_id="c1",
        proposition_text="Chloroplasts contain chlorophyll pigments to absorb solar sunlight for photosynthesis.",
        criterion_text="Chloroplasts contain chlorophyll pigments to absorb sunlight for photosynthesis.",
    )
    res_full = classify([p_full])[0]
    assert res_full.label == Label.FULL_CREDIT
    assert res_full.confidence >= 0.80

    # 2. Misconception match (mitochondria swapped for chloroplasts)
    p_misc = EvalPair(
        prop_id="p_misc",
        criterion_id="c1",
        proposition_text="Mitochondria contain chlorophyll pigments to absorb sunlight for photosynthesis.",
        criterion_text="Chloroplasts contain chlorophyll pigments to absorb sunlight for photosynthesis.",
    )
    res_misc = classify([p_misc])[0]
    assert res_misc.label == Label.MISCONCEPTION

    # 3. No credit match (unrelated claim)
    p_none = EvalPair(
        prop_id="p_none",
        criterion_id="c1",
        proposition_text="Operating systems allocate virtual address spaces to executing threads.",
        criterion_text="Chloroplasts contain chlorophyll pigments to absorb sunlight for photosynthesis.",
    )
    res_none = classify([p_none])[0]
    assert res_none.label == Label.NO_CREDIT


def test_classify_batch_equivalence():
    pairs = [
        EvalPair(
            prop_id=f"p_{i}",
            criterion_id="c1",
            proposition_text=f"Chloroplast statement number {i} absorbs sunlight.",
            criterion_text="Chloroplasts absorb sunlight.",
        )
        for i in range(25)
    ]
    batch_res = classify(pairs)
    single_res = [classify([p])[0] for p in pairs]

    assert len(batch_res) == len(single_res)
    for b, s in zip(batch_res, single_res):
        assert b.id == s.id
        assert b.label == s.label
        assert abs(b.confidence - s.confidence) < 1e-4


def test_missing_model_fail_loudly(monkeypatch):
    monkeypatch.setenv("EVALUATOR_BACKEND", "cpu")
    monkeypatch.setenv("EVALUATOR_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setenv("EVALUATOR_MODEL_PATH", "nonexistent/fake/model/path")

    pair = EvalPair(prop_id="p1", criterion_id="c1", proposition_text="Test", criterion_text="Test")
    with pytest.raises(FileNotFoundError, match="Evaluator weights not found"):
        classify([pair])


def test_missing_model_allow_fallback(monkeypatch):
    monkeypatch.setenv("EVALUATOR_BACKEND", "cpu")
    monkeypatch.setenv("EVALUATOR_ALLOW_MOCK_FALLBACK", "true")
    monkeypatch.setenv("EVALUATOR_MODEL_PATH", "nonexistent/fake/model/path")

    pair = EvalPair(prop_id="p1", criterion_id="c1", proposition_text="Chloroplasts absorb light.", criterion_text="Chloroplasts absorb light.")
    res = classify([pair])
    assert len(res) == 1
    assert res[0].label == Label.FULL_CREDIT


def test_model_info():
    info = model_info()
    assert "backend" in info
    assert "model_path" in info
    assert "taxonomy" in info
    assert len(info["taxonomy"]) == 4
