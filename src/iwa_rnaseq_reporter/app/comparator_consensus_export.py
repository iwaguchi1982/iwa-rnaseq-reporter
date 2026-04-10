from dataclasses import dataclass
from typing import Optional, Tuple
from .comparator_consensus import (
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ComparatorConsensusIssueSpec,
    ComparatorConsensusSummarySpec
)

@dataclass(frozen=True)
class ProvenanceSpec:
    """
    Machine-readable lineage and execution metadata.
    """
    producer_app: str
    producer_version: str
    source_portfolio_id: Optional[str] = None
    source_comparator_run_id: Optional[str] = None
    source_consensus_run_id: Optional[str] = None
    source_bundle_filename: Optional[str] = None
    content_digest: Optional[str] = None

@dataclass(frozen=True)
class ComparatorConsensusManifestSpec:
    """
    Core identity and counts for a consensus analysis run.
    """
    consensus_run_id: str
    n_ranked_comparisons: int
    n_consensus: int
    n_abstain: int
    n_no_consensus: int
    n_insufficient_evidence: int
    # Schema & Provenance (v0.19.1)
    schema_name: str = "ConsensusExportManifest"
    schema_version: str = "0.19.1"
    generated_at: Optional[str] = None
    provenance: Optional[ProvenanceSpec] = None

@dataclass(frozen=True)
class ComparatorConsensusDecisionRowSpec:
    """
    Flattened representation of a consensus decision for tabular export (CSV).
    """
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]
    support_margin: Optional[float]
    has_conflict: bool
    has_weak_support: bool

@dataclass(frozen=True)
class ComparatorConsensusExportPayload:
    """
    Complete collection of serializable data for building the export bundle.
    """
    manifest: ComparatorConsensusManifestSpec
    decision_rows: Tuple[ComparatorConsensusDecisionRowSpec, ...]
    decisions: Tuple[ConsensusDecisionSpec, ...]
    evidence_profiles: Tuple[ConsensusEvidenceProfileSpec, ...]
    issues: Tuple[ComparatorConsensusIssueSpec, ...]
    summary: ComparatorConsensusSummarySpec
