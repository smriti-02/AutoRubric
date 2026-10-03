from pydantic import BaseModel, Field
from .enums import Label
from .document import BBox

class Candidate(BaseModel):
    """A proposition matched to a criterion."""
    prop_id: str
    criterion_id: str
    similarity: float

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "prop_id": "p1",
                "criterion_id": "c1",
                "similarity": 0.85
            }]
        }
    }

class EvalPair(BaseModel):
    """Input pair for the ML Evaluator."""
    prop_id: str
    criterion_id: str
    proposition_text: str = ""
    criterion_text: str = ""
    similarity: float = 0.0

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "prop_id": "p1",
                "criterion_id": "c1",
                "proposition_text": "Plant cells contain chloroplasts.",
                "criterion_text": "Chloroplasts absorb sunlight for photosynthesis.",
                "similarity": 0.85
            }]
        }
    }

class Classification(BaseModel):
    """An ML evaluation label for a proposition/criterion pair."""
    id: str
    prop_id: str
    criterion_id: str
    label: Label
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "cl1",
                "prop_id": "p1",
                "criterion_id": "c1",
                "label": "FULL_CREDIT",
                "confidence": 0.95
            }]
        }
    }

class CriticVerdict(BaseModel):
    """Adversarial check result per classification."""
    classification_id: str
    trusted: bool
    reason: str
    flags: list[str]

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "classification_id": "cl1",
                "trusted": True,
                "reason": "Looks standard.",
                "flags": []
            }]
        }
    }

class CriterionResult(BaseModel):
    """Final score per criterion."""
    criterion_id: str
    label: Label
    credit: float
    marks: float
    evidence_bboxes: list[BBox]
    trusted: bool

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "criterion_id": "c1",
                "label": "FULL_CREDIT",
                "credit": 1.0,
                "marks": 2.0,
                "evidence_bboxes": [{"x": 10.5, "y": 20.0, "w": 100.0, "h": 12.0, "page": 1}],
                "trusted": True
            }]
        }
    }

class ScoreResult(BaseModel):
    """Final output for a document."""
    doc_id: str
    rubric_id: str
    per_criterion: list[CriterionResult]
    total: float
    max_total: float
    needs_review: bool

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "doc_id": "doc123",
                "rubric_id": "r1",
                "per_criterion": [{
                    "criterion_id": "c1",
                    "label": "FULL_CREDIT",
                    "credit": 1.0,
                    "marks": 2.0,
                    "evidence_bboxes": [{"x": 10.5, "y": 20.0, "w": 100.0, "h": 12.0, "page": 1}],
                    "trusted": True
                }],
                "total": 2.0,
                "max_total": 2.0,
                "needs_review": False
            }]
        }
    }
