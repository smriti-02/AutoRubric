import os
from autorubric.contracts import Candidate, Proposition, Rubric
from .matcher import match as _real_match, embed_propositions as _real_embed_propositions

__all__ = ["match", "embed_propositions"]


def match(props: list[Proposition], rubric: Rubric, top_k: int = 3, threshold: float = 0.15) -> list[Candidate]:
    mode = os.environ.get("STAGE_RETRIEVAL_MODE", "real")
    if mode == "stub":
        from .stub import match as _stub_match
        return _stub_match(props, rubric)
    return _real_match(props, rubric, top_k=top_k, threshold=threshold)


def embed_propositions(props: list[Proposition]) -> dict[str, list[float]]:
    mode = os.environ.get("STAGE_RETRIEVAL_MODE", "real")
    if mode == "stub":
        from .stub import embed_propositions as _stub_embed
        return _stub_embed(props)
    return _real_embed_propositions(props)
