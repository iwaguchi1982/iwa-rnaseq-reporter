from dataclasses import dataclass, field
from typing import Optional, Tuple

@dataclass(frozen=True)
class DecisionArtifactRefSpec:
    """
    Comparison-level pointers to relevant artifacts within the bundle.
    All paths are relative to the bundle root.
    """
    consensus_manifest_path: str
    consensus_handoff_contract_path: str
    consensus_decisions_json_path: str
    evidence_profiles_json_path: str
    consensus_decisions_csv_path: str
    report_summary_md_path: str

@dataclass(frozen=True)
class DecisionEvidenceStatsSpec:
    """
    Point-in-time statistics for a specific comparison decision.
    Used for quick-look UI / decision support.
    """
    support_margin: Optional[float]
    has_conflict: bool
    has_weak_support: bool
    n_supporting_references: int
    n_conflicting_references: int
    n_competing_candidates: int

@dataclass(frozen=True)
class DecisionTopReferenceRefSpec:
    """
    Minimal identifier and score for top-tier evidence.
    Can be used for both supporting and conflicting reference lists.
    """
    reference_dataset_id: str
    reference_comparison_id: str
    label_key: Optional[str] = None
    label_display: Optional[str] = None
    integrated_score: Optional[float] = None
    rank: Optional[int] = None

@dataclass(frozen=True)
class DecisionEvidenceRefSpec:
    """
    The central record for a comparison's decision status and evidence summary.
    Designed for downstream decision-support systems.
    Detailed profiles can be fetched via artifact_refs.
    """
    comparison_id: str
    decision_status: str  # Matches ConsensusDecisionSpec.decision_status semantics
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]
    reason_codes: Tuple[str, ...]
    evidence_stats: DecisionEvidenceStatsSpec
    artifact_refs: DecisionArtifactRefSpec
    top_supporting_reference_refs: Tuple[DecisionTopReferenceRefSpec, ...] = ()
    top_conflicting_reference_refs: Tuple[DecisionTopReferenceRefSpec, ...] = ()

@dataclass(frozen=True)
class ComparatorDecisionSupportSummarySpec:
    """
    Aggregated metrics for the decision support payload block.
    """
    n_decision_refs: int
    n_consensus: int
    n_abstain: int
    n_no_consensus: int
    n_insufficient_evidence: int

@dataclass(frozen=True)
class ComparatorDecisionSupportPayload:
    """
    Compact lookup block for downstream handoff.
    Embedded as an optional block in ComparatorConsensusHandoffPayload.
    """
    decision_evidence_refs: Tuple[DecisionEvidenceRefSpec, ...]
    summary: ComparatorDecisionSupportSummarySpec
    schema_name: str = "ComparatorDecisionSupportPayload"
    schema_version: str = "0.19.4.1"
