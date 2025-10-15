from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_architect.models import ProjectSpecification


def test_project_specification_parses_example(tmp_path: Path) -> None:
    example_path = Path("src/agentic_architect/examples/bioinformatics_etl_cli.json")
    data = json.loads(example_path.read_text(encoding="utf-8"))
    spec = ProjectSpecification.from_json(data)
    assert spec.project.name == "bioinformatics-etl-cli"
    assert spec.testing.coverage_threshold == pytest.approx(0.85)


def test_project_specification_parses_requirements_output() -> None:
    example_path = Path("src/agentic_architect/examples/bioinformatics_etl_requirements.json")
    data = json.loads(example_path.read_text(encoding="utf-8"))
    spec = ProjectSpecification.from_json(data)

    assert spec.architecture.pattern == "etl-pipeline"
    assert spec.architecture.components[0].name == "study-discovery"
    assert spec.testing.coverage_threshold == pytest.approx(0.8, abs=1e-6)
