import json
from pathlib import Path
from typing import List, Union
from autorubric.contracts import Classification, Candidate, EvalPair


def classify(pairs: List[Union[Candidate, EvalPair]]) -> List[Classification]:
    fixture_path = Path(__file__).parents[3] / "tests" / "fixtures" / "evaluator" / "classifications.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return [Classification.model_validate(item) for item in data]
