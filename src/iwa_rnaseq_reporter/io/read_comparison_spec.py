import json
from pathlib import Path
from ..models.comparison import ComparisonSpec

def read_comparison_spec(file_path: str | Path) -> ComparisonSpec:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    schema_name = data.get("$schema_name")
    if schema_name != "ComparisonSpec":
        raise ValueError(f"Expected $schema_name 'ComparisonSpec', got '{schema_name}'")
    return ComparisonSpec.from_dict(data)
