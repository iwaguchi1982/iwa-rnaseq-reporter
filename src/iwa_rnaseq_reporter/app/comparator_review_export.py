from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional, Any

@dataclass(frozen=True)
class ComparatorReviewExportManifestSpec:
    """Review bundle identity and provenance snapshot."""
    schema_name: str = "comparator-review-export-manifest"
    schema_version: str = "1.0.0"
    generated_at: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    review_run_id: str = ""
    source_consensus_run_id: str = ""
    n_total_rows: int = 0
    n_annotated_rows: int = 0
    n_unreviewed: int = 0
    n_flagged: int = 0
    n_reviewed: int = 0
    n_handoff_candidate: int = 0
    n_high_priority: int = 0
    n_follow_up_required: int = 0
    export_scope: str = "full_session"
    source_bundle_filename: Optional[str] = None

@dataclass(frozen=True)
class ComparatorReviewExportRowSpec:
    """Flat export row for downstream consumption."""
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]
    support_margin: Optional[float]
    has_conflict: bool
    has_weak_support: bool
    n_supporting_refs: int
    n_conflicting_refs: int
    triage_status: str
    priority: str
    follow_up_required: bool
    review_note: str
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)
    summary_artifact_path: Optional[str] = None

@dataclass(frozen=True)
class ComparatorReviewSummarySpec:
    """Consolidated review metrics for machine consumption."""
    n_total_rows: int
    n_annotated_rows: int
    n_unreviewed: int
    n_flagged: int
    n_reviewed: int
    n_handoff_candidate: int
    n_high_priority: int
    n_follow_up_required: int
    decision_status_counts: Dict[str, int]
    triage_status_counts: Dict[str, int]

@dataclass(frozen=True)
class ComparatorReviewExportPayload:
    """Container for the full export data."""
    manifest: ComparatorReviewExportManifestSpec
    review_rows: Tuple[ComparatorReviewExportRowSpec, ...]
    summary: ComparatorReviewSummarySpec
