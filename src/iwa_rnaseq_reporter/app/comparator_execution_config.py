from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class RankingConfigSpec:
    """
    Formal configuration for the reference ranking phase.
    """
    overlap_weight: float = 0.20
    top_n_overlap_weight: float = 0.30
    concordance_weight: float = 0.20
    correlation_weight: float = 0.30
    tie_tolerance: float = 0.02
    exact_tie_epsilon: float = 1e-9
    score_integration_method: str = "weighted_sum_v1"
    ranking_sort_policy: str = "integrated_score_desc_then_correlation_desc_then_reference_dataset_id_desc"

@dataclass(frozen=True)
class ConsensusDecisionConfigSpec:
    """
    Formal configuration for the consensus decision making phase.
    """
    candidate_sort_policy: str = "mean_integrated_score_desc_then_top_integrated_score_desc_then_n_supporting_references_desc"
    weak_support_mean_threshold: float = 0.30
    consensus_margin_threshold: float = 0.05
    minimum_supporting_references: int = 1
    top_rank_conflict_policy: str = "no_consensus"
    weak_margin_policy: str = "no_consensus"
    insufficient_support_policy: str = "insufficient_evidence"

@dataclass(frozen=True)
class ComparatorExecutionConfigSpec:
    """
    Top-level container for all execution parameters used in a consensus run.
    """
    config_name: str = "ComparatorExecutionConfig"
    config_version: str = "0.19.3"
    config_source: str = "built_in_defaults"
    ranking: RankingConfigSpec = field(default_factory=RankingConfigSpec)
    consensus: ConsensusDecisionConfigSpec = field(default_factory=ConsensusDecisionConfigSpec)

def build_default_ranking_config() -> RankingConfigSpec:
    """Source of truth for default ranking parameters."""
    return RankingConfigSpec()

def build_default_consensus_decision_config() -> ConsensusDecisionConfigSpec:
    """Source of truth for default consensus thresholds."""
    return ConsensusDecisionConfigSpec()

def build_default_comparator_execution_config() -> ComparatorExecutionConfigSpec:
    """Construct the standard execution config block."""
    return ComparatorExecutionConfigSpec(
        ranking=build_default_ranking_config(),
        consensus=build_default_consensus_decision_config()
    )
