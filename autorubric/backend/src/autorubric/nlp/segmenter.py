"""NLP Proposition Segmenter: Convert Token stream into atomic propositions with bounding boxes and coreference."""

from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional
from autorubric.contracts import Token, Proposition, BBox


def _merge_token_bboxes(tokens: List[Token]) -> List[BBox]:
    """Merge token bounding boxes into line-level bounding boxes per page."""
    if not tokens:
        return []

    by_page: Dict[int, List[Token]] = {}
    for t in tokens:
        by_page.setdefault(t.page, []).append(t)

    merged: List[BBox] = []

    for page, page_tokens in by_page.items():
        sorted_tokens = sorted(page_tokens, key=lambda t: (t.bbox.y, t.bbox.x))

        lines: List[List[Token]] = []
        current_line: List[Token] = []

        for t in sorted_tokens:
            if not current_line:
                current_line.append(t)
            else:
                prev = current_line[-1]
                tolerance = max(prev.bbox.h, t.bbox.h, 6.0) * 0.6
                if abs(t.bbox.y - prev.bbox.y) <= tolerance:
                    current_line.append(t)
                else:
                    lines.append(current_line)
                    current_line = [t]
        if current_line:
            lines.append(current_line)

        for line in lines:
            min_x = min(t.bbox.x for t in line)
            max_x = max(t.bbox.x + t.bbox.w for t in line)
            min_y = min(t.bbox.y for t in line)
            max_y = max(t.bbox.y + t.bbox.h for t in line)
            merged.append(
                BBox(
                    x=round(min_x, 2),
                    y=round(min_y, 2),
                    w=round(max(0.0, max_x - min_x), 2),
                    h=round(max(0.0, max_y - min_y), 2),
                    page=page,
                )
            )

    return merged


def _extract_subject(text: str) -> Optional[str]:
    """Extract a likely subject noun phrase from the beginning of a clause."""
    raw = text.strip()
    if not raw:
        return None

    words = raw.split()
    first_word = words[0].lower().rstrip(",.?!;:\"'")
    pronouns = {"it", "they", "this", "these", "there", "that", "we", "you", "i", "he", "she", "and", "but", "so"}
    if first_word in pronouns:
        return None

    common_verbs = {
        "is", "are", "was", "were", "has", "have", "had", "absorbs", "absorb", "produces", "produce",
        "releases", "release", "uses", "use", "contains", "contain", "splits", "split", "creates", "create",
        "converts", "convert", "requires", "require", "occurs", "occur", "acts", "act", "functions", "function",
        "generates", "generate", "synthesizes", "synthesize", "takes", "take", "gives", "give", "moves", "move",
        "binds", "bind", "forms", "form", "breaks", "break"
    }

    if words[0].lower() in {"the", "a", "an"}:
        if len(words) >= 3 and words[2].lower().rstrip(",.?!;:\"'") in common_verbs:
            return f"{words[0]} {words[1]}"
        elif len(words) >= 4 and words[3].lower().rstrip(",.?!;:\"'") in common_verbs:
            return f"{words[0]} {words[1]} {words[2]}"
        elif len(words) >= 2 and words[1].lower().rstrip(",.?!;:\"'") not in common_verbs:
            return f"{words[0]} {words[1]}"
    elif len(words) >= 2 and words[1].lower().rstrip(",.?!;:\"'") in common_verbs:
        return words[0]
    elif len(words) >= 3 and words[2].lower().rstrip(",.?!;:\"'") in common_verbs:
        return f"{words[0]} {words[1]}"

    return None


def _resolve_coreference(claim_text: str, last_subject: Optional[str]) -> str:
    """Resolve leading pronouns like 'It', 'They', 'This' to the last known subject."""
    if not last_subject:
        return claim_text

    text = claim_text.strip()
    pronoun_patterns = [
        (r"^(It\s+)(is|has|produces|creates|absorbs|releases|converts|uses|requires|contains|occurs|acts|functions)\b", f"{last_subject} \\2"),
        (r"^(They\s+)(are|have|produce|create|absorb|release|convert|use|require|contain|occur|act|function)\b", f"{last_subject} \\2"),
        (r"^(This\s+)(is|causes|leads|results|occurs|happens)\b", f"{last_subject} \\2"),
        (r"^It\b", last_subject),
        (r"^They\b", last_subject),
        (r"^This\b", last_subject),
    ]

    for pattern, replacement in pronoun_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
            break

    return text


_SPACY_NLP = None


def _get_spacy_nlp():
    """Lazily load spaCy model en_core_web_sm."""
    global _SPACY_NLP
    if _SPACY_NLP is None:
        try:
            import spacy
            _SPACY_NLP = spacy.load("en_core_web_sm")
        except Exception:
            _SPACY_NLP = False
    return _SPACY_NLP if _SPACY_NLP is not False else None


def _split_into_atomic_claims(text: str) -> List[Tuple[int, int, str]]:
    """
    Split text into atomic claims while keeping character offsets (start, end, raw_text).
    Splits by sentences (via spaCy en_core_web_sm with regex fallback), then coordinated
    clauses / semicolons / bullet points.
    All character spans are retained so no token is lost.
    """
    claims: List[Tuple[int, int, str]] = []

    # Step 1: Sentence boundaries (spaCy with regex fallback)
    nlp = _get_spacy_nlp()
    sentence_spans: List[Tuple[int, int, str]] = []
    if nlp is not None:
        try:
            doc = nlp(text)
            sentence_spans = [
                (sent.start_char, sent.end_char, sent.text)
                for sent in doc.sents
                if sent.text.strip()
            ]
        except Exception:
            sentence_spans = []

    if not sentence_spans:
        sentence_matches = list(re.finditer(r"[^.!?\n]+(?:[.!?]+|\n+|$)", text))
        sentence_spans = [(sm.start(), sm.end(), sm.group(0)) for sm in sentence_matches if sm.group(0).strip()]

    if not sentence_spans:
        if text.strip():
            claims.append((0, len(text), text.strip()))
        return claims

    for s_start, s_end, raw_sentence in sentence_spans:
        if not raw_sentence.strip():
            continue

        # Step 2: Clause subdivision by semicolons or coordinated conjunctions
        sub_splits = list(
            re.finditer(
                r"(?:;\s*|(?<=\w)\s*,\s*(?:and|but|whereas)\s+|\s+(?:and|but|whereas)\s+(?=[A-Z]|[a-z]+(?:\s+[a-z]+){2,}))",
                raw_sentence,
            )
        )

        if not sub_splits:
            claims.append((s_start, s_end, raw_sentence.strip()))
            continue

        clause_spans: List[Tuple[int, int, str]] = []
        last_pos = 0

        for split in sub_splits:
            c_text = raw_sentence[last_pos:split.start()].strip()
            if c_text:
                clause_spans.append((s_start + last_pos, s_start + split.start(), c_text))
            # Start next span from split.start() so conjunction tokens are included
            last_pos = split.start()

        tail_text = raw_sentence[last_pos:].strip()
        if tail_text:
            clause_spans.append((s_start + last_pos, s_start + len(raw_sentence), tail_text))

        # Merge tiny fragments (< 3 words) with adjacent clause
        merged_clauses: List[Tuple[int, int, str]] = []
        for c_start, c_end, c_str in clause_spans:
            words = c_str.split()
            if len(words) < 3 and merged_clauses:
                prev_start, _, prev_str = merged_clauses[-1]
                merged_clauses[-1] = (prev_start, c_end, f"{prev_str} {c_str}".strip())
            else:
                merged_clauses.append((c_start, c_end, c_str))

        if merged_clauses:
            claims.extend(merged_clauses)
        else:
            claims.append((s_start, s_end, raw_sentence.strip()))

    return claims


def segment(tokens: List[Token], doc_id: str = "") -> List[Proposition]:
    """Segment a stream of Token objects into atomic Proposition claims.

    Guarantees:
    - Never merges hidden and visible tokens into the same proposition.
    - Tracks character offsets back to exact token_ids.
    - Computes merged bounding boxes for evidence highlighting.
    - Resolves anaphoric pronouns using rule-based coreference.
    - Deterministic and unique IDs.
    """
    if not tokens:
        return []

    # Sort tokens into canonical reading order (page, then y, then x)
    sorted_tokens = sorted(tokens, key=lambda t: (t.page, t.bbox.y, t.bbox.x))

    # Identify and filter repeated headers/footers across multi-page documents
    pages = {t.page for t in sorted_tokens}
    filtered_tokens: List[Token] = []
    if len(pages) > 1:
        line_occurrences: Dict[str, set[int]] = {}
        for t in sorted_tokens:
            if t.bbox.y < 45 or t.bbox.y > 750:
                line_occurrences.setdefault(t.text.strip().lower(), set()).add(t.page)

        repeated_texts = {text for text, p_set in line_occurrences.items() if len(p_set) >= len(pages) * 0.75}
        for t in sorted_tokens:
            if t.text.strip().lower() in repeated_texts and (t.bbox.y < 45 or t.bbox.y > 750):
                continue
            filtered_tokens.append(t)
    else:
        filtered_tokens = sorted_tokens

    # Chunk tokens by (page, block_id, is_hidden) to strictly isolate hidden text
    chunks: List[List[Token]] = []
    current_chunk: List[Token] = []
    current_key: Optional[Tuple[int, str, bool]] = None

    for t in filtered_tokens:
        key = (t.page, t.block_id, t.is_hidden)
        if key != current_key:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [t]
            current_key = key
        else:
            current_chunk.append(t)
    if current_chunk:
        chunks.append(current_chunk)

    propositions: List[Proposition] = []
    prop_counter = 0
    last_known_subject: Optional[str] = None

    for chunk in chunks:
        if not chunk:
            continue

        page = chunk[0].page
        is_hidden = chunk[0].is_hidden

        chunk_text_parts: List[str] = []
        char_to_token: List[Optional[Token]] = []

        for i, t in enumerate(chunk):
            if i > 0:
                chunk_text_parts.append(" ")
                char_to_token.append(None)

            word = t.text
            chunk_text_parts.append(word)
            for _ in range(len(word)):
                char_to_token.append(t)

        chunk_text = "".join(chunk_text_parts)
        if not chunk_text.strip():
            continue

        # Split into atomic claims
        atomic_claims = _split_into_atomic_claims(chunk_text)

        for c_start, c_end, raw_claim in atomic_claims:
            clean_text = raw_claim.strip()
            if not clean_text:
                continue

            # Strip leading question/enumeration prefixes like "Q1.", "Ans:", "1."
            clean_text = re.sub(r"^(?:Q\d+[\.:]?\s*|Ans[\.:]?\s*|\d+[\.:]\s*|[-•*]\s*)", "", clean_text).strip()
            # Also clean leading coordination like ", and " or "and " for cleaner proposition proposition text
            clean_text = re.sub(r"^(?:,\s*)?(?:and|but|whereas)\s+", "", clean_text, flags=re.IGNORECASE).strip()
            if not clean_text:
                continue

            # Map claim characters back to token_ids (tokens spanned by the entire clause)
            claim_tokens_dict: Dict[str, Token] = {}
            for char_idx in range(c_start, min(c_end, len(char_to_token))):
                tok = char_to_token[char_idx]
                if tok is not None:
                    claim_tokens_dict[tok.id] = tok

            claim_tokens = list(claim_tokens_dict.values())
            if not claim_tokens:
                continue

            # Update coreference
            subj = _extract_subject(clean_text)
            if subj:
                last_known_subject = subj
                resolved_text = clean_text
            else:
                resolved_text = _resolve_coreference(clean_text, last_known_subject)

            merged_bboxes = _merge_token_bboxes(claim_tokens)

            prop_counter += 1
            prop_id = f"p{page}_{prop_counter}" if not doc_id else f"p_{doc_id}_{page}_{prop_counter}"

            propositions.append(
                Proposition(
                    id=prop_id,
                    doc_id=doc_id,
                    text=resolved_text,
                    token_ids=[t.id for t in claim_tokens],
                    page=page,
                    bboxes=merged_bboxes,
                    from_hidden_text=is_hidden,
                )
            )

    return propositions
