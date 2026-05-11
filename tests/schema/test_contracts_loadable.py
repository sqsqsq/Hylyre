"""L4 schema smoke: contract files load."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def test_output_schema_is_valid_json_schema() -> None:
    path = ROOT / "hylyre" / "contracts" / "output-schema.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)


def test_report_sections_yaml_loads() -> None:
    path = ROOT / "hylyre" / "contracts" / "report-sections.yaml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "report_required_sections" in data
    assert data["execution_status_values"]
