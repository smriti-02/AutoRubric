"""Rubric compiler: validate raw rubric JSON and build a dependency graph."""

from __future__ import annotations

import networkx as nx
from pydantic import ValidationError

from autorubric.contracts import Rubric

_REQUIRED_TOP_LEVEL = ("id", "title", "criteria", "credit_map", "max_score")


def _format_cycle(cycle: list) -> str:
    """Render a networkx cycle (list of edges) as ``a -> b -> a``."""
    if not cycle:
        return ""
    path = [edge[0] for edge in cycle] + [cycle[-1][1]]
    return " -> ".join(path)


def _add_valid_edges(graph: nx.DiGraph, criteria: list[dict], known: set[str]) -> None:
    graph.add_nodes_from(known)
    for criterion in criteria:
        cid = criterion["id"]
        for dep in criterion["depends_on"]:
            if dep in known and dep != cid:
                graph.add_edge(dep, cid)


def compile_rubric(json_data: dict) -> Rubric:
    """Validate ``json_data`` against the :class:`Rubric` contract.

    Every validation failure is collected and raised together in a single
    :class:`ValueError` rather than stopping at the first problem.
    """
    if not isinstance(json_data, dict):
        raise ValueError("Invalid rubric: expected a JSON object")

    errors: list[str] = []

    for key in _REQUIRED_TOP_LEVEL:
        if key not in json_data:
            errors.append(f"Missing required field: {key!r}")

    raw_criteria = json_data.get("criteria", [])
    if not isinstance(raw_criteria, list):
        errors.append("'criteria' must be a list of objects")
        raw_criteria = []
    elif not raw_criteria:
        errors.append("Rubric must contain at least one criterion")

    parsed: list[dict] = []
    id_to_index: dict[str, int] = {}
    duplicates: set[str] = set()

    for index, raw in enumerate(raw_criteria):
        if not isinstance(raw, dict):
            errors.append(f"criteria[{index}] must be an object")
            continue

        cid = raw.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f"criteria[{index}] has a missing or empty 'id'")
            continue

        if cid in id_to_index:
            duplicates.add(cid)
        else:
            id_to_index[cid] = index

        deps = raw.get("depends_on", [])
        parsed.append(
            {
                "id": cid,
                "description": raw.get("description"),
                "weight": raw.get("weight"),
                "depends_on": deps if isinstance(deps, list) else [],
            }
        )
        if not isinstance(deps, list):
            errors.append(f"Criterion {cid!r} has a non-list 'depends_on'")

    for cid in sorted(duplicates):
        errors.append(f"Duplicate criterion id: {cid!r}")

    known = set(id_to_index)

    for criterion in parsed:
        cid = criterion["id"]

        description = criterion["description"]
        if not isinstance(description, str) or not description.strip():
            errors.append(f"Criterion {cid!r} has an empty description")

        weight = criterion["weight"]
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            errors.append(f"Criterion {cid!r} has a non-numeric weight: {weight!r}")
        elif weight <= 0:
            errors.append(f"Criterion {cid!r} has a non-positive weight: {weight}")

        normalized_deps: list[str] = []
        for dep in criterion["depends_on"]:
            if not isinstance(dep, str):
                errors.append(f"Criterion {cid!r} has a non-string dependency: {dep!r}")
                continue
            normalized_deps.append(dep)
            if dep == cid:
                errors.append(f"Criterion {cid!r} depends on itself")
            elif dep not in known:
                errors.append(f"Criterion {cid!r} depends on unknown criterion {dep!r}")
        criterion["depends_on"] = normalized_deps

    graph = nx.DiGraph()
    _add_valid_edges(graph, parsed, known)
    if known:
        try:
            cycle = nx.find_cycle(graph, orientation="original")
        except nx.NetworkXNoCycle:
            cycle = []
        if cycle:
            errors.append(f"Dependency cycle detected: {_format_cycle(cycle)}")

    if errors:
        details = "\n".join(f" - {error}" for error in errors)
        raise ValueError(f"Invalid rubric ({len(errors)} error(s)):\n{details}")

    try:
        return Rubric.model_validate(json_data)
    except ValidationError as exc:
        details = "\n".join(
            f" - {'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise ValueError(f"Invalid rubric schema:\n{details}") from exc


def topological_order(rubric: Rubric) -> list[str]:
    """Return criterion IDs ordered so dependencies come before dependents."""
    graph = nx.DiGraph()
    ids = [criterion.id for criterion in rubric.criteria]
    graph.add_nodes_from(ids)
    known = set(ids)

    for criterion in rubric.criteria:
        for dep in criterion.depends_on:
            if dep in known and dep != criterion.id:
                graph.add_edge(dep, criterion.id)

    try:
        return list(nx.topological_sort(graph))
    except nx.NetworkXUnfeasible as exc:
        cycle = nx.find_cycle(graph, orientation="original")
        raise ValueError(f"Dependency cycle detected: {_format_cycle(cycle)}") from exc
