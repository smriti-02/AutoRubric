import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple
from autorubric.contracts import CollusionReport
from autorubric.contracts.collusion import DocPairMatch

@dataclass
class CollusionConfig:
    prop_threshold: float = 0.85
    pair_absolute_threshold: float = 0.70
    z_score_threshold: float = 1.5
    top_n: int = 10

def detect(cohort_embeddings: Dict[str, Dict[str, List[float]]], config: CollusionConfig = None) -> CollusionReport:
    if config is None:
        config = CollusionConfig()

    if isinstance(cohort_embeddings, list):
        cohort_embeddings = {
            item.get("doc_id", str(i)): item.get("embeddings", {}) if isinstance(item, dict) else {}
            for i, item in enumerate(cohort_embeddings)
        }

    doc_ids = list(cohort_embeddings.keys())
    
    if len(doc_ids) < 2:
        return CollusionReport(cohort_id="unknown", doc_pairs=[])
        
    # Check for empty docs or vector size mismatch
    vec_size = None
    doc_props = {}
    doc_vectors = {}
    
    for d_id, props in cohort_embeddings.items():
        doc_props[d_id] = list(props.keys())
        vectors = []
        for p_id in doc_props[d_id]:
            v = np.array(props[p_id], dtype=np.float32)
            if vec_size is None:
                vec_size = v.shape[0]
            elif v.shape[0] != vec_size:
                raise ValueError(f"Vector size mismatch: expected {vec_size}, got {v.shape[0]}")
            # L2 normalize
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            vectors.append(v)
        
        if vectors:
            doc_vectors[d_id] = np.stack(vectors)
        else:
            doc_vectors[d_id] = np.empty((0, vec_size if vec_size else 1))

    pairs = []
    pair_similarities = []

    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            a_id = doc_ids[i]
            b_id = doc_ids[j]
            
            vec_a = doc_vectors[a_id]
            vec_b = doc_vectors[b_id]
            
            if len(vec_a) == 0 or len(vec_b) == 0:
                continue
                
            # Cosine similarity matrix (already L2 normalized)
            sim_matrix = vec_a @ vec_b.T
            
            # Greedy match
            matched_a = set()
            matched_b = set()
            matching_props = []
            
            # Sort by highest similarity
            # Flat indices of sorted elements
            flat_indices = np.argsort(sim_matrix, axis=None)[::-1]
            
            sum_sim = 0.0
            
            for idx in flat_indices:
                r, c = np.unravel_index(idx, sim_matrix.shape)
                sim = sim_matrix[r, c]
                if sim < config.prop_threshold:
                    break # Since it's sorted descending
                
                if r not in matched_a and c not in matched_b:
                    matched_a.add(r)
                    matched_b.add(c)
                    sum_sim += sim
                    matching_props.append(f"{doc_props[a_id][r]}::{doc_props[b_id][c]}")
            
            num_matches = len(matching_props)
            min_len = min(len(vec_a), len(vec_b))
            
            if min_len > 0 and num_matches > 0:
                frac = num_matches / min_len
                mean_sim = sum_sim / num_matches
                pair_sim = 0.5 * frac + 0.5 * mean_sim
            else:
                pair_sim = 0.0

            pairs.append({
                "doc_a": a_id,
                "doc_b": b_id,
                "similarity": float(pair_sim),
                "matching_props": matching_props
            })
            pair_similarities.append(pair_sim)
            
    if not pairs:
        return CollusionReport(cohort_id="unknown", doc_pairs=[])
        
    pair_similarities = np.array(pair_similarities)
    mean_sim = np.mean(pair_similarities)
    std_sim = np.std(pair_similarities)
    
    doc_pairs = []
    
    for p in pairs:
        # absolute check
        if p["similarity"] < config.pair_absolute_threshold:
            continue
            
        is_suspicious = False
        
        # relative check if cohort is large enough
        if len(doc_ids) >= 5:
            if std_sim > 0:
                z_score = (p["similarity"] - mean_sim) / std_sim
                if z_score >= config.z_score_threshold:
                    is_suspicious = True
            else:
                # no variance but exceeds absolute threshold
                is_suspicious = True
        else:
            is_suspicious = True
            
        if is_suspicious:
            doc_pairs.append(DocPairMatch(
                a=p["doc_a"],
                b=p["doc_b"],
                similarity=p["similarity"],
                matching_props=p["matching_props"]
            ))
            
    doc_pairs.sort(key=lambda x: x.similarity, reverse=True)
    doc_pairs = doc_pairs[:config.top_n]
    
    return CollusionReport(
        cohort_id="unknown",
        doc_pairs=doc_pairs
    )
