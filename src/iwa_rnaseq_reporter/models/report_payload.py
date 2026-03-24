from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class ReportSection:
    section_key: str
    section_type: str
    source_refs: List[str] = field(default_factory=list)

@dataclass
class ReportArtifact:
    artifact_type: str
    path: str

@dataclass
class ReportPayloadSpec:
    schema_name: str
    schema_version: str
    report_payload_id: str
    project_id: str
    title: str
    sections: List[ReportSection] = field(default_factory=list)
    artifacts: List[ReportArtifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    overlay: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["$schema_name"] = d.pop("schema_name")
        d["$schema_version"] = d.pop("schema_version")
        return {k: v for k, v in d.items() if v is not None}
