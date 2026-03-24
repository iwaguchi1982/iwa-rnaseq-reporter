from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class ComparisonGroup:
    label: str
    criteria: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonGroup":
        return cls(
            label=data.get("label", ""),
            criteria=data.get("criteria", {})
        )

@dataclass
class SampleSelectorFilters:
    inclusion: List[Dict[str, Any]] = field(default_factory=list)
    exclusion: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SampleSelectorFilters":
        if not data: return cls()
        return cls(
            inclusion=data.get("inclusion", []),
            exclusion=data.get("exclusion", [])
        )


@dataclass
class ComparisonSpec:
    schema_name: str
    schema_version: str
    comparison_id: str
    comparison_type: str
    input_matrix_id: str
    sample_selector: Optional[SampleSelectorFilters] = None
    groups: List[ComparisonGroup] = field(default_factory=list)
    paired: bool = False
    covariates: List[str] = field(default_factory=list)
    analysis_intent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    overlay: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["$schema_name"] = d.pop("schema_name")
        d["$schema_version"] = d.pop("schema_version")
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonSpec":
        selector_data = data.get("sample_selector")
        sel = SampleSelectorFilters.from_dict(selector_data) if selector_data else None
        gps = [ComparisonGroup.from_dict(g) for g in data.get("groups", [])]

        return cls(
            schema_name=data.get("$schema_name", ""),
            schema_version=data.get("$schema_version", ""),
            comparison_id=data.get("comparison_id", ""),
            comparison_type=data.get("comparison_type", ""),
            input_matrix_id=data.get("input_matrix_id", ""),
            sample_selector=sel,
            groups=gps,
            paired=data.get("paired", False),
            covariates=data.get("covariates", []),
            analysis_intent=data.get("analysis_intent", ""),
            metadata=data.get("metadata", {}),
            overlay=data.get("overlay", {})
        )
