from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_engine import ComparatorScoreSpec
from .comparator_ranking_input import ComparatorNormalizedScoreSpec, ComparatorRankingInputContext
from .comparator_execution_config import RankingConfigSpec, build_default_ranking_config

@dataclass(frozen=True)
class ComparatorIntegratedRankingScoreSpec:
    """
    Weighted integration of multiple normalized scoring indicators.
    """
    integrated_score: float
    overlap_component: Optional[float]
    top_n_overlap_component: Optional[float]
    concordance_component: Optional[float]
    correlation_component: Optional[float]

@dataclass(frozen=True)
class ComparatorRankedReferenceSpec:
    """
    A specific reference match with its relative rank within a comparison.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    rank: int
    integrated_score: ComparatorIntegratedRankingScoreSpec
    raw_score: ComparatorScoreSpec
    normalized_score: ComparatorNormalizedScoreSpec
    ranking_flags: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorTopRankConflictSpec:
    """
    Detection of non-unique or closely competing top references for a comparison.
    """
    comparison_id: str
    top_reference_ids: Tuple[str, ...]
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorRankingIssueSpec:
    """
    Warnings related to the ranking process.
    """
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None
    reference_dataset_id: Optional[str] = None
    reference_comparison_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorRankingSummarySpec:
    """
    High-level metrics for the ranking phase.
    """
    n_rankable_matches: int
    n_ranked_comparisons: int
    n_top_rank_conflicts: int
    is_ready_for_consensus_labeling: bool

@dataclass(frozen=True)
class ComparatorRankingContext:
    """
    The final results of reference-level ranking, acting as the primary
    input for biological consensus labeling (v0.18.3).
    """
    ranking_input_context: ComparatorRankingInputContext
    ranked_references: Tuple[ComparatorRankedReferenceSpec, ...]
    top_rank_conflicts: Tuple[ComparatorTopRankConflictSpec, ...]
    issues: Tuple[ComparatorRankingIssueSpec, ...]
    summary: ComparatorRankingSummarySpec
    # v0.19.3: Execution config contract
    ranking_config: RankingConfigSpec = field(default_factory=RankingConfigSpec)
