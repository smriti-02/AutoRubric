import os
from autorubric.contracts import Rubric, Proposition, Token
from .compiler import compile_rubric, topological_order

__all__ = ["compile_rubric", "topological_order", "segment"]


def segment(tokens: list[Token], doc_id: str = "") -> list[Proposition]:
    mode = os.environ.get("STAGE_SEGMENTATION_MODE", "real")
    if mode == "stub":
        from .stub import segment as _segment
    else:
        from .segmenter import segment as _segment
    return _segment(tokens, doc_id=doc_id)
