from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_engine import ComparatorScoreSpec, ComparatorResultContext

@dataclass(frozen=True)
class ComparatorNormalizedScoreSpec:
    """
    Comparison indicators normalized to a common scale (mostly 0.0 - 1.0)
    to enable balanced weighted ranking.
    """
    overlap_score: Optional[float]
    top_n_overlap_score: Optional[float]
    concordance_score: Optional[float]
    correlation_score: Optional[float]

@dataclass(frozen=True)
class ComparatorRankableMatchSpec:
    """
    A match that has passed basic eligibility criteria and is ready for ranking.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    raw_score: ComparatorScoreSpec
    normalized_score: ComparatorNormalizedScoreSpec
    eligibility_flags: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorNonRankableMatchSpec:
    """
    A match that was excluded from ranking due to insufficient evidence quality.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorRankingIssueSpec:
    """
    Warnings related to the ranking input preparation.
    """
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None
    reference_dataset_id: Optional[str] = None
    reference_comparison_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorRankingInputSummarySpec:
    """
    High-level metrics for the ranking input context.
    """
    n_successful_matches: int
    n_rankable_matches: int
    n_non_rankable_matches: int
    n_comparisons_with_rankable_matches: int
    has_only_weak_evidence: bool
    is_ready_for_reference_ranking: bool

@dataclass(frozen=True)
class ComparatorRankingInputContext:
    """
    Standardized inputs for the ranking layer (v0.18.2).
    Derivative of ComparatorResultContext.
    """
    result_context: ComparatorResultContext
    rankable_matches: Tuple[ComparatorRankableMatchSpec, ...]
    non_rankable_matches: Tuple[ComparatorNonRankableMatchSpec, ...]
    issues: Tuple[ComparatorRankingIssueSpec, ...]
    summary: ComparatorRankingInputSummarySpec
