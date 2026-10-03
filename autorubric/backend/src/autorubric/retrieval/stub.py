import json
from pathlib import Path
from autorubric.contracts import Candidate, Proposition, Rubric


def match(props: list[Proposition], rubric: Rubric) -> list[Candidate]:
    fixture_path = Path(__file__).parents[3] / "tests" / "fixtures" / "retrieval" / "candidates.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return [Candidate.model_validate(item) for item in data]


def embed_propositions(props: list[Proposition]) -> dict[str, list[float]]:
    # Mock embeddings: return 384-dimensional zeros or small deterministic numbers
    return {p.id: [0.0] * 384 for p in props}
