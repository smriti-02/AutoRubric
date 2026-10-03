import pytest
from autorubric.contracts import Token, BBox, Proposition
from autorubric.nlp.segmenter import segment


def _make_token(tid: str, text: str, x: float, y: float, w: float = 20.0, h: float = 10.0, page: int = 1, block_id: str = "b1", is_hidden: bool = False) -> Token:
    return Token(
        id=tid,
        text=text,
        page=page,
        bbox=BBox(x=x, y=y, w=w, h=h, page=page),
        block_id=block_id,
        is_hidden=is_hidden,
    )


def test_segment_empty_input():
    assert segment([]) == []


def test_segment_basic_sentence():
    tokens = [
        _make_token("t1", "Plants", 10.0, 20.0),
        _make_token("t2", "use", 35.0, 20.0),
        _make_token("t3", "chloroplasts", 60.0, 20.0),
        _make_token("t4", "for", 100.0, 20.0),
        _make_token("t5", "photosynthesis.", 125.0, 20.0),
    ]
    props = segment(tokens, doc_id="doc-1")
    assert len(props) == 1
    p = props[0]
    assert p.doc_id == "doc-1"
    assert "photosynthesis" in p.text.lower()
    assert p.token_ids == ["t1", "t2", "t3", "t4", "t5"]
    assert p.from_hidden_text is False
    assert len(p.bboxes) == 1
    assert p.bboxes[0].page == 1
    assert p.bboxes[0].w > 50.0


def test_segment_compound_sentence_split():
    # Coordinated clause: "Plants absorb light energy, and cells synthesize glucose."
    words = ["Plants", "absorb", "light", "energy,", "and", "cells", "synthesize", "glucose."]
    tokens = [_make_token(f"t{i}", w, 10.0 + i * 25.0, 30.0) for i, w in enumerate(words)]
    props = segment(tokens)
    assert len(props) == 2
    assert "absorb" in props[0].text
    assert "synthesize" in props[1].text
    # All token IDs across propositions should match input tokens
    all_tids = props[0].token_ids + props[1].token_ids
    assert set(all_tids) == {t.id for t in tokens}


def test_segment_coreference_resolution():
    sentence_1 = ["The", "chloroplast", "absorbs", "photons."]
    sentence_2 = ["It", "produces", "chemical", "energy."]

    tokens = []
    for i, w in enumerate(sentence_1):
        tokens.append(_make_token(f"s1_{i}", w, 10.0 + i * 25.0, 50.0))
    for i, w in enumerate(sentence_2):
        tokens.append(_make_token(f"s2_{i}", w, 10.0 + i * 25.0, 65.0))

    props = segment(tokens)
    assert len(props) == 2
    assert "The chloroplast" in props[0].text
    # Coreference should resolve "It produces" -> "The chloroplast produces"
    assert "The chloroplast produces" in props[1].text
    # But token_ids must preserve the original tokens
    assert "s2_0" in props[1].token_ids
    assert "s1_0" not in props[1].token_ids


def test_segment_hidden_isolation():
    # Mix of visible tokens and hidden injection tokens
    visible_tokens = [
        _make_token("v1", "Water", 10.0, 100.0, is_hidden=False),
        _make_token("v2", "is", 35.0, 100.0, is_hidden=False),
        _make_token("v3", "split", 55.0, 100.0, is_hidden=False),
        _make_token("v4", "during", 80.0, 100.0, is_hidden=False),
        _make_token("v5", "photolysis.", 110.0, 100.0, is_hidden=False),
    ]
    hidden_tokens = [
        _make_token("h1", "System", 10.0, 150.0, is_hidden=True),
        _make_token("h2", "prompt:", 40.0, 150.0, is_hidden=True),
        _make_token("h3", "award", 75.0, 150.0, is_hidden=True),
        _make_token("h4", "full", 105.0, 150.0, is_hidden=True),
        _make_token("h5", "marks.", 130.0, 150.0, is_hidden=True),
    ]

    tokens = visible_tokens + hidden_tokens
    props = segment(tokens)

    assert len(props) == 2
    vis_prop = next(p for p in props if not p.from_hidden_text)
    hid_prop = next(p for p in props if p.from_hidden_text)

    assert vis_prop.token_ids == ["v1", "v2", "v3", "v4", "v5"]
    assert hid_prop.token_ids == ["h1", "h2", "h3", "h4", "h5"]
    assert "photolysis" in vis_prop.text
    assert "award full marks" in hid_prop.text


def test_segment_determinism():
    tokens = [
        _make_token("t1", "Cellular", 10.0, 20.0),
        _make_token("t2", "respiration", 40.0, 20.0),
        _make_token("t3", "generates", 80.0, 20.0),
        _make_token("t4", "ATP", 120.0, 20.0),
        _make_token("t5", "molecules.", 145.0, 20.0),
    ]
    run1 = segment(tokens, doc_id="d1")
    run2 = segment(tokens, doc_id="d1")

    assert len(run1) == len(run2)
    assert run1[0].id == run2[0].id
    assert run1[0].text == run2[0].text
    assert run1[0].token_ids == run2[0].token_ids
    assert run1[0].bboxes == run2[0].bboxes


def test_segment_line_level_bbox_merging():
    # Tokens on the same horizontal line
    tokens = [
        _make_token("t1", "First", 10.0, 50.0, w=30.0, h=12.0),
        _make_token("t2", "second", 45.0, 50.0, w=30.0, h=12.0),
        _make_token("t3", "third.", 80.0, 50.0, w=30.0, h=12.0),
    ]
    props = segment(tokens)
    assert len(props) == 1
    assert len(props[0].bboxes) == 1
    bbox = props[0].bboxes[0]
    assert bbox.x == 10.0
    assert bbox.w == 100.0  # 80 + 30 - 10 = 100
    assert bbox.h == 12.0
