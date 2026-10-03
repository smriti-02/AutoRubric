import json
import pytest
from pathlib import Path
from autorubric.pipeline.graph import build_graph
from autorubric.contracts import JobStatus, Rubric
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import autorubric.core.db

# Removed global mock

def test_pipeline_end_to_end():
    graph = build_graph()
    
    fixture_path = Path(__file__).parents[1] / "fixtures" / "rubrics" / "rubric.json"
    with open(fixture_path) as f:
        rubric = Rubric.model_validate(json.load(f))
        
    from autorubric.core.config import config
    config.STAGE_EXTRACTION_MODE = "mock"
    config.STAGE_SEGMENTATION_MODE = "mock"
    config.STAGE_RETRIEVAL_MODE = "mock"
    config.STAGE_EVALUATION_MODE = "mock"
    config.STAGE_AUDIT_MODE = "mock"
    config.STAGE_ANNOTATION_MODE = "mock"

    pdf_path = Path(__file__).parents[1] / "fixtures" / "extraction" / "clean_single_column.pdf"
    pdf_bytes = pdf_path.read_bytes()

    initial_state = {
        "doc_id": "doc123",
        "rubric": rubric,
        "pdf_bytes": pdf_bytes,
        "status": JobStatus.QUEUED
    }
    
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args, **kwargs):
            from autorubric.contracts import JobStatus
            class DummyJob:
                status = JobStatus.QUEUED
            return DummyJob()
        def add(self, *args, **kwargs): pass
        async def commit(self): pass
        async def execute(self, *args, **kwargs):
            class DummyResult:
                def scalars(self): return self
                def first(self): return None
            return DummyResult()

    with patch("autorubric.core.db.AsyncSessionLocal", return_value=DummySession()):
        result = graph.invoke(initial_state)
    
    assert result["status"] == JobStatus.DONE
    assert result["score"] is not None
    assert result["score"].doc_id == "doc123"
    assert result["annotated_pdf"] is not None
