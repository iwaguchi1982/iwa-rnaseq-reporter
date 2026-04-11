from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_consensus import ComparatorConsensusSummarySpec
from .comparator_consensus_export import ProvenanceSpec
from .comparator_execution_config import ComparatorExecutionConfigSpec
from .comparator_decision_support import ComparatorDecisionSupportPayload

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
    # Schema & Provenance (v0.19.1/v0.19.3)
    schema_name: str = "ConsensusHandoffContract"
    schema_version: str = "0.19.3"
    generated_at: Optional[str] = None
    provenance: Optional[ProvenanceSpec] = None
    # v0.19.3: Execution config contract
    execution_config: Optional[ComparatorExecutionConfigSpec] = None
    # v0.19.4.1: Compact decision support contract
    decision_support: Optional[ComparatorDecisionSupportPayload] = None
