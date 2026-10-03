"""
AutoRubric Full End-to-End Pipeline Demonstration Script.

Runs the complete rubric grading pipeline locally on a sample submission PDF:
1. Compile Rubric DAG
2. Extract Document Tokens & Bounding Boxes
3. Segment into Atomic Proposition Units
4. Match Candidate Evidence via Embeddings
5. Classify & Evaluate Credit Criteria
6. Audit for Prompt Injections & Anomalies (Critic)
7. Score & Apply Dependency Caps
8. Annotate & Generate Visual PDF Feedback
"""

import sys
import json
from pathlib import Path

# Add backend src to python path
backend_src = Path(__file__).resolve().parents[1] / "backend" / "src"
fixtures_dir = Path(__file__).resolve().parents[1] / "backend" / "tests" / "fixtures"
sys.path.insert(0, str(backend_src))

from autorubric.nlp.compiler import compile_rubric
from autorubric.extraction import extract
from autorubric.nlp import segment
from autorubric.retrieval import match
from autorubric.evaluator import classify
from autorubric.audit import audit
from autorubric.scorer import score
from autorubric.annotation import annotate
from autorubric.contracts import Rubric


def run_demo():
    print("=" * 70)
    print("  AutoRubric Full End-to-End Pipeline Demonstration")
    print("=" * 70)

    # 1. Load and Compile Rubric
    rubric_file = fixtures_dir / "rubrics" / "rubric.json"
    with open(rubric_file, "r") as f:
        rubric_data = json.load(f)
    rubric_id = rubric_data.get('rubric_id') or rubric_data.get('id')
    print(f"\n[1/7] Compiling Rubric: '{rubric_data['title']}' ({rubric_id})...")
    compiled_dag = compile_rubric(rubric_data)
    rubric = Rubric.model_validate(rubric_data)
    print(f"      Compiled {len(compiled_dag.criteria)} criteria successfully.")
    for crit in compiled_dag.criteria:
        deps = f" (depends on: {crit.depends_on})" if crit.depends_on else ""
        print(f"      - [{crit.id}] {crit.description[:50]}... (weight={crit.weight}){deps}")

    # 2. Extract Document Tokens
    pdf_path = fixtures_dir / "extraction" / "clean_single_column.pdf"
    print(f"\n[2/7] Extracting PDF Tokens from '{pdf_path.name}'...")
    pdf_bytes = pdf_path.read_bytes()
    tokens = extract(pdf_bytes)
    print(f"      Extracted {len(tokens)} text tokens with bounding boxes across pages.")

    # 3. Proposition Segmentation
    print(f"\n[3/7] Segmenting into Atomic Proposition Units...")
    propositions = segment(tokens)
    print(f"      Generated {len(propositions)} proposition segments.")
    for idx, p in enumerate(propositions[:3]):
        print(f"      - Prop #{idx+1} [page {p.page}]: \"{p.text}\" (tokens={len(p.token_ids)})")
    if len(propositions) > 3:
        print(f"      ... and {len(propositions) - 3} more.")

    # 4. Retrieval Matching
    print(f"\n[4/7] Matching Propositions Against Criteria Candidates...")
    candidates = match(propositions, rubric, top_k=3, threshold=0.0)
    print(f"      Retrieved {len(candidates)} criterion-proposition candidate pairs.")

    # 5. Semantic Evaluation / Classification
    print(f"\n[5/7] Evaluating & Classifying Criteria Credit...")
    classifications = classify(candidates)
    for c in classifications:
        print(f"      - Criterion [{c.criterion_id}]: {c.label.value} (conf={c.confidence:.2f})")

    # 6. Critic & Security Audit
    print(f"\n[6/7] Auditing Classifications for Injections & Anomalies...")
    verdicts = audit(classifications, tokens, propositions, candidates)
    all_trusted = all(v.trusted for v in verdicts)
    print(f"      Critic Verdicts: All Trusted = {all_trusted} ({len(verdicts)} evaluated)")
    for v in verdicts:
        if v.flags:
            print(f"      ! Flag on [{v.classification_id}]: {', '.join(v.flags)} - {v.reason}")
    if all_trusted:
        print("      No malicious injections, hidden text, or anomalies detected.")

    # 7. Scorer & Annotation
    print(f"\n[7/7] Computing Final Weighted Scores & Annotating PDF...")
    score_result = score(classifications, rubric, verdicts)
    print(f"      Total Score: {score_result.total:.1f} / {score_result.max_total:.1f} (needs_review={score_result.needs_review})")
    for r in score_result.per_criterion:
        trusted_str = "TRUSTED" if r.trusted else "UNTRUSTED"
        print(f"      - [{r.criterion_id}] Marks: {r.marks:.1f} ({r.label.value}) [{trusted_str}]")

    annotated_pdf = annotate(pdf_bytes, score_result)
    print(f"      Annotated PDF generated successfully ({len(annotated_pdf)} bytes).")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETED SUCCESSFULLY: End-to-End Pipeline Verified!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
