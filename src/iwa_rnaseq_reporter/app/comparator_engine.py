from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_matching import ComparatorMatchingContext

@dataclass(frozen=True)
class ComparatorScoreSpec:
    """
    Core statistical indicators representing the similarity between two comparisons.
    """
    n_overlap_features: int
    n_top_n_overlap_features: int
    direction_concordance: Optional[float]
    signed_effect_correlation: Optional[float]

@dataclass(frozen=True)
class ComparatorMatchResultSpec:
    """
    The calculated score result for a specific pair of experimental and reference comparisons.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    experimental_result_path: str
    reference_result_ref: str
    score: ComparatorScoreSpec

@dataclass(frozen=True)
class ComparatorSkippedMatchSpec:
    """
    Record of a match that could not be computed due to missing data or technical issues.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorEngineIssueSpec:
    """
    Warnings or informational issues discovered during the scoring phase.
    """
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None
    reference_dataset_id: Optional[str] = None
    reference_comparison_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorResultSummarySpec:
    """
    High-level metrics for the comparison engine execution.
    """
    n_total_matches_requested: int
    n_successful_matches: int
    n_skipped_matches: int
    n_comparisons_with_results: int
    is_ready_for_export: bool

@dataclass(frozen=True)
class ComparatorResultContext:
    """
    Comprehensive context holding all scoring results and engine execution logs.
    Final source of truth for downstream handoff.
    """
    matching_context: ComparatorMatchingContext
    match_results: Tuple[ComparatorMatchResultSpec, ...]
    skipped_matches: Tuple[ComparatorSkippedMatchSpec, ...]
    issues: Tuple[ComparatorEngineIssueSpec, ...]
    summary: ComparatorResultSummarySpec
