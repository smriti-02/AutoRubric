import math
import pytest
from autorubric.contracts import Proposition, BBox, Rubric, Candidate
from autorubric.retrieval.matcher import match, embed_propositions


def _make_prop(pid: str, text: str) -> Proposition:
    return Proposition(
        id=pid,
        doc_id="doc1",
        text=text,
        token_ids=[f"t_{pid}"],
        page=1,
        bboxes=[BBox(x=10.0, y=20.0, w=100.0, h=12.0, page=1)],
        from_hidden_text=False,
    )


def _make_rubric():
    return Rubric(
        id="r-bio",
        title="Photosynthesis",
        max_score=6.0,
        credit_map={"FULL_CREDIT": 1.0, "PARTIAL_CREDIT": 0.5, "NO_CREDIT": 0.0, "MISCONCEPTION": 0.0},
        criteria=[
            {"id": "c1", "description": "Chloroplasts absorb sunlight for energy.", "weight": 2.0, "depends_on": []},
            {"id": "c2", "description": "Water photolysis releases oxygen.", "weight": 2.0, "depends_on": []},
            {"id": "c3", "description": "Carbon dioxide is fixed into glucose.", "weight": 2.0, "depends_on": []},
        ],
    )


def test_embed_propositions_empty():
    assert embed_propositions([]) == {}


def test_embed_propositions_shape_and_normalisation():
    props = [
        _make_prop("p1", "Chloroplasts capture photons from light."),
        _make_prop("p2", "Water molecules split into oxygen and protons."),
    ]
    embeddings = embed_propositions(props)
    assert set(embeddings.keys()) == {"p1", "p2"}

    for pid, vec in embeddings.items():
        assert len(vec) == 384
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-3


def test_match_empty_inputs():
    rubric = _make_rubric()
    assert match([], rubric) == []


def test_match_ordering_and_top_k():
    rubric = _make_rubric()
    props = [
        _make_prop("p1", "Chloroplasts contain chlorophyll that absorbs light photons."),
        _make_prop("p2", "Water is split releasing oxygen gas."),
    ]

    candidates = match(props, rubric, top_k=2, threshold=0.0)
    assert len(candidates) > 0

    # Ensure for each prop_id, candidates are sorted by similarity descending
    for pid in ["p1", "p2"]:
        prop_cands = [c for c in candidates if c.prop_id == pid]
        assert len(prop_cands) <= 2
        for i in range(len(prop_cands) - 1):
            assert prop_cands[i].similarity >= prop_cands[i + 1].similarity

    # For p1, top match should be c1 (chloroplasts)
    p1_top = [c for c in candidates if c.prop_id == "p1"][0]
    assert p1_top.criterion_id == "c1"

    # For p2, top match should be c2 (water photolysis)
    p2_top = [c for c in candidates if c.prop_id == "p2"][0]
    assert p2_top.criterion_id == "c2"


def test_match_threshold_filtering():
    rubric = _make_rubric()
    props = [_make_prop("p1", "Unrelated economics topic about inflation and interest rates.")]
    # High threshold should filter out this completely off-topic proposition
    candidates = match(props, rubric, top_k=3, threshold=0.9)
    assert len(candidates) == 0


def test_match_determinism():
    rubric = _make_rubric()
    props = [_make_prop("p1", "Chloroplasts absorb sunlight for energy.")]

    cands_1 = match(props, rubric, top_k=3, threshold=0.1)
    cands_2 = match(props, rubric, top_k=3, threshold=0.1)

    assert len(cands_1) == len(cands_2)
    for c1, c2 in zip(cands_1, cands_2):
        assert c1.prop_id == c2.prop_id
        assert c1.criterion_id == c2.criterion_id
        assert abs(c1.similarity - c2.similarity) < 1e-5
