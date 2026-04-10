from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_ranking import ComparatorRankingContext

@dataclass(frozen=True)
class ConsensusSupportingReferenceSpec:
    """
    A ranked reference that supports the decided consensus label.
    """
    comparison_id: str
    label_key: str
    reference_dataset_id: str
    reference_comparison_id: str
    integrated_score: float
    rank: int

@dataclass(frozen=True)
class ConsensusConflictingReferenceSpec:
    """
    A ranked reference that contradicts the decided consensus label.
    """
    comparison_id: str
    label_key: str
    reference_dataset_id: str
    reference_comparison_id: str
    integrated_score: float
    rank: int

@dataclass(frozen=True)
class ConsensusLabelCandidateSpec:
    """
    Aggregate metrics for a specific biological label across all matches.
    """
    comparison_id: str
    label_key: str
    label_display: str
    n_supporting_references: int
    mean_integrated_score: float
    top_integrated_score: float
    supporting_reference_ids: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ConsensusEvidenceProfileSpec:
    """
    The structured relationship between support and conflict for a comparison.
    """
    comparison_id: str
    top_candidate: Optional[ConsensusLabelCandidateSpec]
    competing_candidates: Tuple[ConsensusLabelCandidateSpec, ...]
    supporting_references: Tuple[ConsensusSupportingReferenceSpec, ...]
    conflicting_references: Tuple[ConsensusConflictingReferenceSpec, ...]
    support_margin: Optional[float]
    has_conflict: bool
    has_weak_support: bool

@dataclass(frozen=True)
class ConsensusDecisionSpec:
    """
    The final automated decision for a biological state.
    """
    comparison_id: str
    decision_status: str  # "consensus" | "abstain" | "no_consensus" | "insufficient_evidence"
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]
    reason_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorConsensusIssueSpec:
    """
    Warnings related to the consensus aggregation.
    """
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorConsensusSummarySpec:
    """
    High-level metrics for the consensus phase.
    """
    n_ranked_comparisons: int
    n_consensus: int
    n_abstain: int
    n_no_consensus: int
    n_insufficient_evidence: int
    is_ready_for_consensus_export: bool

@dataclass(frozen=True)
class ComparatorConsensusContext:
    """
    The final interpreted results of the comparison pipeline.
    Final source of truth for the entire suite (v0.18.4).
    """
    ranking_context: ComparatorRankingContext
    decisions: Tuple[ConsensusDecisionSpec, ...]
    evidence_profiles: Tuple[ConsensusEvidenceProfileSpec, ...]
    issues: Tuple[ComparatorConsensusIssueSpec, ...]
    summary: ComparatorConsensusSummarySpec
