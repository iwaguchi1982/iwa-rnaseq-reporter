from dataclasses import dataclass, field
from typing import Optional, Any
from .comparator_review_session import ComparatorReviewRowSpec

@dataclass(frozen=True)
class ComparatorReviewReferenceDetailSpec:
    """Compact detail for a single contributing reference comparison."""
    reference_dataset_id: str
    reference_comparison_id: str
    label_key: Optional[str] = None
    label_display: Optional[str] = None
    integrated_score: Optional[float] = None
    rank: Optional[int] = None

@dataclass(frozen=True)
class ComparatorReviewArtifactDetailSpec:
    """Container for relative paths to various consensus artifacts."""
    consensus_manifest_path: Optional[str] = None
    consensus_handoff_contract_path: Optional[str] = None
    consensus_decisions_json_path: Optional[str] = None
    evidence_profiles_json_path: Optional[str] = None
    consensus_decisions_csv_path: Optional[str] = None
    report_summary_md_path: Optional[str] = None

@dataclass(frozen=True)
class ComparatorReviewDecisionDetailSpec:
    """Formal decision and evidence summary for a single comparison."""
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str] = None
    decided_label_display: Optional[str] = None
    support_margin: Optional[float] = None
    has_conflict: bool = False
    has_weak_support: bool = False
    n_supporting_refs: int = 0
    n_conflicting_refs: int = 0
    n_competing_candidates: Optional[int] = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    top_supporting_refs: tuple[ComparatorReviewReferenceDetailSpec, ...] = field(default_factory=tuple)
    top_conflicting_refs: tuple[ComparatorReviewReferenceDetailSpec, ...] = field(default_factory=tuple)
    artifacts: ComparatorReviewArtifactDetailSpec = field(default_factory=ComparatorReviewArtifactDetailSpec)

@dataclass(frozen=True)
class ComparatorReviewJsonInspectionSpec:
    """Container for raw JSON payloads for troubleshooting."""
    decision_json: Optional[dict] = None
    evidence_profile_json: Optional[dict] = None

@dataclass(frozen=True)
class ComparatorReviewDrilldownContext:
    """Aggregated context for the detail pane of a selected comparison."""
    selected_comparison_id: str
    row: ComparatorReviewRowSpec
    decision_detail: ComparatorReviewDecisionDetailSpec
    json_inspection: ComparatorReviewJsonInspectionSpec
    issues: tuple[str, ...] = field(default_factory=tuple)
