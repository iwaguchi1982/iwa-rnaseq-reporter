from dataclasses import dataclass, field
from typing import Tuple, Dict
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewRowSpec,
    ComparatorReviewSessionContext
)

@dataclass(frozen=True)
class ComparatorReviewFilterSpec:
    """
    State of the review table filters.
    """
    decision_statuses: Tuple[str, ...] = field(default_factory=tuple)
    decided_label_keys: Tuple[str, ...] = field(default_factory=tuple)
    conflict_mode: str = "all"  # "all" | "conflict_only" | "no_conflict_only"
    weak_support_mode: str = "all"  # "all" | "weak_only" | "not_weak_only"
    search_query: str = ""

@dataclass(frozen=True)
class ComparatorReviewTableSummarySpec:
    """
    Aggregated metrics for the filtered review table rows.
    """
    n_total_rows: int
    n_filtered_rows: int
    n_consensus: int
    n_no_consensus: int
    n_insufficient_evidence: int
    n_with_conflict: int
    n_with_weak_support: int
    decision_status_counts: Dict[str, int] = field(default_factory=dict)
    decided_label_counts: Dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class ComparatorReviewTableContext:
    """
    The final state ready for UI rendering.
    """
    source_session: ComparatorReviewSessionContext
    filters: ComparatorReviewFilterSpec
    filtered_rows: Tuple[ComparatorReviewRowSpec, ...]
    summary: ComparatorReviewTableSummarySpec
