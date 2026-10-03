import pytest
from autorubric.nlp.compiler import compile_rubric, topological_order


def sample_valid_rubric_dict():
    return {
        "id": "r-valid-1",
        "title": "Valid Independent Rubric",
        "max_score": 10.0,
        "credit_map": {
            "FULL_CREDIT": 1.0,
            "PARTIAL_CREDIT": 0.5,
            "NO_CREDIT": 0.0,
            "MISCONCEPTION": 0.0,
        },
        "criteria": [
            {
                "id": "c1",
                "description": "Explains light dependent reactions.",
                "weight": 5.0,
                "depends_on": [],
            },
            {
                "id": "c2",
                "description": "Explains light independent Calvin cycle.",
                "weight": 5.0,
                "depends_on": [],
            },
        ],
    }


def test_compile_valid_rubric():
    data = sample_valid_rubric_dict()
    rubric = compile_rubric(data)
    assert rubric.id == "r-valid-1"
    assert len(rubric.criteria) == 2
    assert rubric.max_score == 10.0
    order = topological_order(rubric)
    assert set(order) == {"c1", "c2"}


def test_compile_diamond_dependency_graph():
    # c1 is root, c2 and c3 depend on c1, c4 depends on c2 and c3 (diamond)
    data = {
        "id": "r-diamond",
        "title": "Diamond Dependency Rubric",
        "max_score": 10.0,
        "credit_map": {
            "FULL_CREDIT": 1.0,
            "PARTIAL_CREDIT": 0.5,
            "NO_CREDIT": 0.0,
            "MISCONCEPTION": 0.0,
        },
        "criteria": [
            {"id": "c1", "description": "Foundation", "weight": 2.0, "depends_on": []},
            {"id": "c2", "description": "Branch A", "weight": 3.0, "depends_on": ["c1"]},
            {"id": "c3", "description": "Branch B", "weight": 3.0, "depends_on": ["c1"]},
            {"id": "c4", "description": "Synthesis", "weight": 2.0, "depends_on": ["c2", "c3"]},
        ],
    }
    rubric = compile_rubric(data)
    order = topological_order(rubric)
    assert order.index("c1") < order.index("c2")
    assert order.index("c1") < order.index("c3")
    assert order.index("c2") < order.index("c4")
    assert order.index("c3") < order.index("c4")


def test_compile_invalid_input_type():
    with pytest.raises(ValueError, match="expected a JSON object"):
        compile_rubric(["not", "a", "dict"])


def test_compile_missing_top_level_fields():
    with pytest.raises(ValueError) as exc:
        compile_rubric({"id": "r1"})
    msg = str(exc.value)
    assert "Missing required field: 'title'" in msg
    assert "Missing required field: 'criteria'" in msg


def test_compile_empty_criteria_list():
    data = sample_valid_rubric_dict()
    data["criteria"] = []
    with pytest.raises(ValueError, match="at least one criterion"):
        compile_rubric(data)


def test_compile_duplicate_criterion_id():
    data = sample_valid_rubric_dict()
    data["criteria"].append(
        {"id": "c1", "description": "Duplicate id c1", "weight": 2.0, "depends_on": []}
    )
    with pytest.raises(ValueError, match="Duplicate criterion id: 'c1'"):
        compile_rubric(data)


def test_compile_empty_criterion_description():
    data = sample_valid_rubric_dict()
    data["criteria"][0]["description"] = "   "
    with pytest.raises(ValueError, match="empty description"):
        compile_rubric(data)


def test_compile_non_positive_and_non_numeric_weight():
    data = sample_valid_rubric_dict()
    data["criteria"][0]["weight"] = 0
    with pytest.raises(ValueError, match="non-positive weight"):
        compile_rubric(data)

    data["criteria"][0]["weight"] = "five"
    with pytest.raises(ValueError, match="non-numeric weight"):
        compile_rubric(data)


def test_compile_self_dependency():
    data = sample_valid_rubric_dict()
    data["criteria"][0]["depends_on"] = ["c1"]
    with pytest.raises(ValueError, match="depends on itself"):
        compile_rubric(data)


def test_compile_unknown_dependency():
    data = sample_valid_rubric_dict()
    data["criteria"][0]["depends_on"] = ["c_nonexistent"]
    with pytest.raises(ValueError, match="unknown criterion 'c_nonexistent'"):
        compile_rubric(data)


def test_compile_dependency_cycle():
    data = sample_valid_rubric_dict()
    data["criteria"][0]["depends_on"] = ["c2"]
    data["criteria"][1]["depends_on"] = ["c1"]
    with pytest.raises(ValueError, match="Dependency cycle detected"):
        compile_rubric(data)


def test_compile_weight_sum_mismatch():
    data = sample_valid_rubric_dict()
    data["max_score"] = 25.0  # weights sum to 10.0 != 25.0
    with pytest.raises(ValueError, match="must equal max_score"):
        compile_rubric(data)


def test_compile_multi_error_report():
    # Multiple errors together: duplicate id, self dep, negative weight, empty description
    data = {
        "id": "r-multi",
        "title": "Multi-error Rubric",
        "max_score": 10.0,
        "credit_map": {"FULL_CREDIT": 1.0, "PARTIAL_CREDIT": 0.5, "NO_CREDIT": 0.0, "MISCONCEPTION": 0.0},
        "criteria": [
            {"id": "c1", "description": "", "weight": -2.0, "depends_on": ["c1"]},
            {"id": "c1", "description": "Duplicate", "weight": 5.0, "depends_on": ["ghost"]},
        ],
    }
    with pytest.raises(ValueError) as exc:
        compile_rubric(data)
    msg = str(exc.value)
    assert "Duplicate criterion id: 'c1'" in msg
    assert "empty description" in msg
    assert "non-positive weight" in msg
    assert "depends on itself" in msg
    assert "unknown criterion 'ghost'" in msg
