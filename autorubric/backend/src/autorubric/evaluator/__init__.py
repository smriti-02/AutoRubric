import os
from typing import List, Union
from autorubric.contracts import Classification, Candidate, EvalPair
from .classifier import classify as _real_classify, model_info

__all__ = ["classify", "model_info"]


def classify(pairs: List[Union[Candidate, EvalPair]]) -> List[Classification]:
    mode = os.environ.get("STAGE_EVALUATION_MODE", "real")
    if mode == "stub":
        from .stub import classify as _stub_classify
        return _stub_classify(pairs)
    return _real_classify(pairs)
