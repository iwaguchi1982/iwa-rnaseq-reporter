from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_intake import ComparatorIntakeContext
from .reference_dataset_registry import ReferenceDatasetRegistry

@dataclass(frozen=True)
class ComparatorMatchedReferenceSpec:
    """
    Indicates that an experimental comparison matches a specific reference comparison.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    matrix_kind: str
    feature_id_system: str

@dataclass(frozen=True)
class ComparatorUnmatchedComparisonSpec:
    """
    Placeholder for an experimental comparison that had no compatible references.
    """
    comparison_id: str
    comparison_label: str
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorMatchingIssueSpec:
    """
    Warnings or informational issues discovered during the matching phase.
    """
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None
    reference_dataset_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorMatchingSummarySpec:
    """
    High-level metrics for the matching phase.
    """
    n_accepted_comparisons: int
    n_matched_comparisons: int
    n_unmatched_comparisons: int
    n_total_matches: int
    is_ready_for_comparison_engine: bool

@dataclass(frozen=True)
class ComparatorMatchingContext:
    """
    Comprehensive context holding the results of matching experimental 
    comparisons against the reference registry.
    """
    intake_context: ComparatorIntakeContext
    registry: ReferenceDatasetRegistry
    matched_references: Tuple[ComparatorMatchedReferenceSpec, ...]
    unmatched_comparisons: Tuple[ComparatorUnmatchedComparisonSpec, ...]
    issues: Tuple[ComparatorMatchingIssueSpec, ...]
    summary: ComparatorMatchingSummarySpec
