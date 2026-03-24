from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class ResultRow:
    feature_id: str
    feature_label: Optional[str] = None
    effect_size: Optional[float] = None
    effect_type: Optional[str] = None
    p_value: Optional[float] = None
    q_value: Optional[float] = None
    direction: Optional[str] = None
    base_mean: Optional[float] = None

@dataclass
class ResultProvenance:
    method: str
    method_version: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResultSpec:
    schema_name: str
    schema_version: str
    result_id: str
    comparison_id: str
    result_kind: str
    feature_type: str
    rows: List[ResultRow] = field(default_factory=list)
    provenance: Optional[ResultProvenance] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    overlay: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["$schema_name"] = d.pop("schema_name")
        d["$schema_version"] = d.pop("schema_version")
        return {k: v for k, v in d.items() if v is not None}
