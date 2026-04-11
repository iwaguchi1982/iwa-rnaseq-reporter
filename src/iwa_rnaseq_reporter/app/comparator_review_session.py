from dataclasses import dataclass, field
from typing import Optional, Tuple

@dataclass(frozen=True)
class ComparatorReviewRowSpec:
    """
    A normalized, flattened representation of a single comparison for review triage.
    Synthesizes data from decisions and evidence profiles into a presentation-ready format.
    """
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str] = None
    decided_label_display: Optional[str] = None
    support_margin: Optional[float] = None
    has_conflict: bool = False
    has_weak_support: bool = False
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)
    n_supporting_refs: int = 0
    n_conflicting_refs: int = 0
    top_supporting_ref_ids: Tuple[str, ...] = field(default_factory=tuple)
    top_conflicting_ref_ids: Tuple[str, ...] = field(default_factory=tuple)
    
    # Artifact Pointers (Source of truth: handoff artifact_refs)
    decision_artifact_path: Optional[str] = None
    evidence_artifact_path: Optional[str] = None
    summary_artifact_path: Optional[str] = None
    
    # Review workflow placeholders (v0.20.2+)
    review_bucket: str = "all"
    search_text: str = ""
    is_actionable: bool = True

@dataclass(frozen=True)
class ComparatorReviewSessionSummarySpec:
    """
    Aggregated metrics for the current review session.
    """
    n_total_rows: int
    n_consensus: int
    n_no_consensus: int
    n_insufficient_evidence: int
    n_with_conflict: int
    n_with_weak_support: int
    n_without_decided_label: int
    
    # Bucket distribution for convenience
    decision_status_counts: dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class ComparatorReviewSessionContext:
    """
    The complete intake model loaded from a consensus bundle for the researcher.
    """
    source_consensus_run_id: str
    rows: Tuple[ComparatorReviewRowSpec, ...]
    summary: ComparatorReviewSessionSummarySpec
    source_bundle_filename: Optional[str] = None
    issues: Tuple[str, ...] = field(default_factory=tuple)
    included_comparison_ids: Tuple[str, ...] = field(default_factory=tuple)
    decided_label_keys: Tuple[str, ...] = field(default_factory=tuple)
