from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_consensus import ComparatorConsensusSummarySpec

@dataclass(frozen=True)
class ComparatorConsensusBundleRefSpec:
    """
    Relative path references to files within the consensus bundle.
    """
    consensus_bundle_filename: str
    consensus_manifest_path: str
    consensus_summary_path: str
    consensus_decisions_path: str
    evidence_profiles_path: str
    consensus_handoff_contract_path: str

@dataclass(frozen=True)
class ComparatorConsensusComparisonRefSpec:
    """
    Quick-lookup summary ref for a specific comparison ID.
    Used by downstream tools to decide which results to load.
    """
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]

@dataclass(frozen=True)
class ComparatorConsensusHandoffPayload:
    """
    The official contract for downstream consumption of consensus results.
    """
    consensus_run_id: str
    bundle_refs: ComparatorConsensusBundleRefSpec
    included_comparison_ids: Tuple[str, ...]
    decided_label_keys: Tuple[str, ...]
    comparison_decision_refs: Tuple[ComparatorConsensusComparisonRefSpec, ...]
    summary: ComparatorConsensusSummarySpec
