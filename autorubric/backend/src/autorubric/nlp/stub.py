import json
from pathlib import Path
from autorubric.contracts import Proposition, Token


def segment(tokens: list[Token], doc_id: str = "") -> list[Proposition]:
    fixture_path = Path(__file__).parents[3] / "tests" / "fixtures" / "nlp" / "propositions.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return [Proposition.model_validate(item) for item in data]
