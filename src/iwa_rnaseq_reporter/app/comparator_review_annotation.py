from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

@dataclass(frozen=True)
class ComparatorReviewAnnotationSpec:
    """Reviewer-managed triage state for a single comparison."""
    comparison_id: str
    triage_status: str  # unreviewed, flagged, reviewed, handoff_candidate
    priority: str       # normal, high
    review_note: str = ""
    follow_up_required: bool = False
    updated_at: Optional[str] = None

@dataclass(frozen=True)
class ComparatorReviewAnnotationSummarySpec:
    """Aggregated progress metrics for the review session."""
    n_total_rows: int
    n_annotated_rows: int
    n_unreviewed: int
    n_flagged: int
    n_reviewed: int
    n_handoff_candidate: int
    n_high_priority: int
    n_follow_up_required: int

@dataclass(frozen=True)
class ComparatorReviewAnnotationStore:
    """In-memory collection of reviewer annotations for a specific consensus bundle."""
    source_consensus_run_id: str
    annotations: Dict[str, ComparatorReviewAnnotationSpec] = field(default_factory=dict)
    summary: Optional[ComparatorReviewAnnotationSummarySpec] = None
