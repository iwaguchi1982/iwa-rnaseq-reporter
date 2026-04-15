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
class ReportIdentitySpec:
    comparison_id: str
    comparison_label: str
    comparison_column: Optional[str] = None
    group_a_label: Optional[str] = None
    group_b_label: Optional[str] = None
    sample_count_group_a: Optional[int] = None
    sample_count_group_b: Optional[int] = None

@dataclass
class ReportSummarySnapshot:
    n_features_tested: int
    n_sig_up: Optional[int] = None
    n_sig_down: Optional[int] = None
    max_abs_log2_fc: Optional[float] = None

@dataclass
class ReportDisplayContextSnapshot:
    padj_threshold: Optional[float] = None
    abs_log2_fc_threshold: Optional[float] = None
    sort_by: Optional[str] = None
    preview_top_n: Optional[int] = None
    matrix_kind: Optional[str] = None
    normalization: Optional[str] = None

@dataclass
class ReportNarrativeSlot:
    slot_key: str
    title: str
    text: Optional[str] = None
    source_refs: List[str] = field(default_factory=list)

@dataclass
class ReportPayloadSpec:
    schema_name: str
    schema_version: str
    report_payload_id: str
    project_id: str
    title: str
    identity: Optional[ReportIdentitySpec] = None
    summary: Optional[ReportSummarySnapshot] = None
    display_context: Optional[ReportDisplayContextSnapshot] = None
    narrative_slots: List[ReportNarrativeSlot] = field(default_factory=list)
    sections: List[ReportSection] = field(default_factory=list)
    artifacts: List[ReportArtifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    overlay: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["$schema_name"] = d.pop("schema_name")
        d["$schema_version"] = d.pop("schema_version")
        return {k: v for k, v in d.items() if v is not None}
