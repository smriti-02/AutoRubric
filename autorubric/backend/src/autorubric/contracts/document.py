from pydantic import BaseModel, Field

class BBox(BaseModel):
    """Bounding box coordinates in PDF points (origin top-left)."""
    x: float
    y: float
    w: float
    h: float
    page: int

    model_config = {
        "json_schema_extra": {
            "examples": [{"x": 10.5, "y": 20.0, "w": 100.0, "h": 12.0, "page": 1}]
        }
    }

class Token(BaseModel):
    """A word token extracted from a PDF."""
    id: str
    text: str
    page: int
    bbox: BBox
    block_id: str
    is_hidden: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "t1",
                "text": "photosynthesis",
                "page": 1,
                "bbox": {"x": 10.5, "y": 20.0, "w": 100.0, "h": 12.0, "page": 1},
                "block_id": "b1",
                "is_hidden": False
            }]
        }
    }

class Proposition(BaseModel):
    """An atomic claim extracted from a document."""
    id: str
    doc_id: str = ""
    text: str
    token_ids: list[str]
    page: int
    bboxes: list[BBox]
    from_hidden_text: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "p1",
                "doc_id": "doc123",
                "text": "The plant cell has a chloroplast.",
                "token_ids": ["t1", "t2"],
                "page": 1,
                "bboxes": [{"x": 10.5, "y": 20.0, "w": 100.0, "h": 12.0, "page": 1}],
                "from_hidden_text": False
            }]
        }
    }
