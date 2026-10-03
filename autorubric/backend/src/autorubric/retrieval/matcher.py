"""Sentence Embedding and Candidate Retrieval Module."""

from __future__ import annotations

import os
import math
import hashlib
from typing import List, Dict, Optional, Tuple
import numpy as np

from autorubric.contracts import Candidate, Proposition, Rubric

_MODEL = None
_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_CRITERION_CACHE: Dict[Tuple[str, str], np.ndarray] = {}


def _get_model():
    """Lazily load the sentence-transformers model once per process."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer(_MODEL_NAME)
        except Exception as exc:
            # Documented fallback if network/weights are unavailable
            _MODEL = "fallback"
    return _MODEL


def _fallback_embed(text: str, dim: int = 384) -> np.ndarray:
    """Deterministic, normalized pseudo-embedding based on character n-grams and hashing."""
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        vec[0] = 1.0
        return vec

    for i, word in enumerate(words):
        # 3-gram hashing
        for j in range(len(word) - 2):
            gram = word[j:j+3]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:6], 16) % dim
            vec[h] += 1.0 / (i + 1)
        # Word hash
        h_word = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:6], 16) % dim
        vec[h_word] += 2.0 / (i + 1)

    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    else:
        vec[0] = 1.0
    return vec


def _encode_texts(texts: List[str]) -> np.ndarray:
    """Encode a list of text strings into L2-normalized 2D numpy array [N, 384]."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = _get_model()
    if model != "fallback":
        try:
            embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.astype(np.float32)
        except Exception:
            pass

    # Use deterministic fallback if model encode failed or model is fallback
    encoded = [_fallback_embed(t) for t in texts]
    return np.array(encoded, dtype=np.float32)


def embed_propositions(props: List[Proposition]) -> Dict[str, List[float]]:
    """Generate normalized sentence embeddings for propositions.

    Returns:
        dict mapping prop_id to 384-dimensional vector.
        Used by the collusion detector in P5.
    """
    if not props:
        return {}

    texts = [p.text for p in props]
    matrix = _encode_texts(texts)

    result: Dict[str, List[float]] = {}
    for prop, vec in zip(props, matrix):
        result[prop.id] = [float(x) for x in vec]
    return result


def _get_criterion_embeddings(rubric: Rubric) -> Dict[str, np.ndarray]:
    """Retrieve or compute cached embeddings for rubric criteria."""
    result: Dict[str, np.ndarray] = {}
    missing_crit: List[Tuple[str, str]] = []

    for c in rubric.criteria:
        cache_key = (rubric.id, c.id)
        if cache_key in _CRITERION_CACHE:
            result[c.id] = _CRITERION_CACHE[cache_key]
        else:
            missing_crit.append((c.id, c.description))

    if missing_crit:
        descriptions = [desc for _, desc in missing_crit]
        embeddings = _encode_texts(descriptions)
        for (cid, _), vec in zip(missing_crit, embeddings):
            _CRITERION_CACHE[(rubric.id, cid)] = vec
            result[cid] = vec

    return result


def match(
    props: List[Proposition],
    rubric: Rubric,
    top_k: int = 3,
    threshold: float = 0.15,
) -> List[Candidate]:
    """Match student propositions against rubric criteria via cosine similarity.

    Args:
        props: List of extracted propositions (including hidden-text ones).
        rubric: Rubric with criteria descriptions.
        top_k: Maximum number of criteria per proposition.
        threshold: Minimum cosine similarity score.

    Returns:
        List of Candidate(prop_id, criterion_id, similarity) sorted by similarity.
    """
    if not props or not rubric.criteria:
        return []

    # Get proposition embeddings
    prop_texts = [p.text for p in props]
    prop_vectors = _encode_texts(prop_texts)

    # Get criterion embeddings
    crit_dict = _get_criterion_embeddings(rubric)
    crit_ids = list(crit_dict.keys())
    crit_vectors = np.array([crit_dict[cid] for cid in crit_ids], dtype=np.float32)

    # Cosine similarity matrix: [num_props, num_criteria]
    # Since vectors are L2-normalized, cosine similarity is simply the matrix dot product
    similarity_matrix = np.dot(prop_vectors, crit_vectors.T)

    candidates: List[Candidate] = []

    for i, prop in enumerate(props):
        scores = similarity_matrix[i]
        # Pair each criterion with its score
        paired = [(crit_ids[j], float(scores[j])) for j in range(len(crit_ids))]
        # Filter by threshold
        valid = [item for item in paired if item[1] >= threshold]
        # Sort by similarity descending, ties broken by criterion id ascending
        sorted_pairs = sorted(valid, key=lambda x: (-x[1], x[0]))

        # Take top-k
        for cid, sim in sorted_pairs[:top_k]:
            candidates.append(
                Candidate(
                    prop_id=prop.id,
                    criterion_id=cid,
                    similarity=round(sim, 4),
                )
            )

    return candidates
