import json
from pathlib import Path
from autorubric.contracts import (
    Token, Proposition, Candidate, Rubric, Classification,
    CriticVerdict, ScoreResult, JobStatus
)
from autorubric.pipeline.state import PipelineState
from autorubric.extraction import extract
from autorubric.nlp import segment
from autorubric.retrieval import match, embed_propositions
from autorubric.evaluator import classify
from autorubric.scorer import score
from autorubric.audit import audit, detect
from autorubric.annotation import annotate

def load_fixture(module, filename):
    fixture_path = Path(__file__).parents[1] / "fixtures" / module / filename
    with open(fixture_path) as f:
        return json.load(f)

def load_pdf_fixture(filename="clean_single_column.pdf") -> bytes:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "extraction" / filename
    return fixture_path.read_bytes()

def test_extraction_conformance():
    tokens = extract(load_pdf_fixture())
    assert isinstance(tokens, list)
    assert all(isinstance(t, Token) for t in tokens)

def test_segmentation_conformance():
    tokens = extract(load_pdf_fixture())
    props = segment(tokens)
    assert isinstance(props, list)
    assert all(isinstance(p, Proposition) for p in props)
    
    # Invariant: every Proposition.token_ids exists in the input tokens
    token_ids = {t.id for t in tokens}
    for p in props:
        for tid in p.token_ids:
            assert tid in token_ids

def test_retrieval_conformance():
    rubric_data = load_fixture("rubrics", "rubric.json")
    rubric = Rubric.model_validate(rubric_data)
    
    tokens = extract(load_pdf_fixture())
    props = segment(tokens)
    
    candidates = match(props, rubric)
    assert isinstance(candidates, list)
    assert all(isinstance(c, Candidate) for c in candidates)
    
    # Invariant: every Candidate references real propositions and criteria
    prop_ids = {p.id for p in props}
    crit_ids = {c.id for c in rubric.criteria}
    for c in candidates:
        assert c.prop_id in prop_ids
        assert c.criterion_id in crit_ids
        
    embed_propositions(props) # should not crash

def test_evaluator_conformance():
    rubric_data = load_fixture("rubrics", "rubric.json")
    rubric = Rubric.model_validate(rubric_data)
    tokens = extract(load_pdf_fixture())
    props = segment(tokens)
    candidates = match(props, rubric)
    
    classifications = classify(candidates)
    assert isinstance(classifications, list)
    assert all(isinstance(c, Classification) for c in classifications)
    
    # Invariant: every Classification.prop_id exists
    prop_ids = {p.id for p in props}
    crit_ids = {c.id for c in rubric.criteria}
    for c in classifications:
        assert c.prop_id in prop_ids
        assert c.criterion_id in crit_ids

def test_scorer_conformance():
    rubric_data = load_fixture("rubrics", "rubric.json")
    rubric = Rubric.model_validate(rubric_data)
    tokens = extract(load_pdf_fixture())
    props = segment(tokens)
    candidates = match(props, rubric)
    classifications = classify(candidates)
    
    score_result = score(classifications, rubric, [])
    assert isinstance(score_result, ScoreResult)

def test_audit_conformance():
    verdicts = audit([], [], [])
    assert isinstance(verdicts, list)

def test_annotation_conformance():
    rubric_data = load_fixture("rubrics", "rubric.json")
    rubric = Rubric.model_validate(rubric_data)
    pdf_bytes = load_pdf_fixture()
    tokens = extract(pdf_bytes)
    props = segment(tokens)
    candidates = match(props, rubric)
    classifications = classify(candidates)
    score_result = score(classifications, rubric, [])
    pdf = annotate(pdf_bytes, score_result)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0

def test_nlp_detect_conformance():
    # detect takes a list of doc data (doc_id, text, embeddings, etc.) or just anything to return a CollusionReport
    report = detect([{"doc_id": "1", "text": "foo"}, {"doc_id": "2", "text": "foo"}])
    assert isinstance(report.cohort_id, str)
