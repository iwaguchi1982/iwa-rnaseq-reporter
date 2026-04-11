from dataclasses import dataclass, field
from typing import Tuple, Optional, Any, Dict
from .comparator_review_export import ComparatorReviewSummarySpec

@dataclass(frozen=True)
class ComparatorReviewBundleRefSpec:
    """Relative paths to artifacts within the review bundle."""
    review_bundle_filename: str
    review_manifest_path: str = "review_manifest.json"
    review_rows_json_path: str = "review_rows.json"
    review_rows_csv_path: str = "review_rows.csv"
    review_summary_json_path: str = "review_summary.json"
    review_summary_md_path: str = "review_summary.md"
    review_handoff_contract_path: str = "review_handoff_contract.json"

@dataclass(frozen=True)
class ComparatorReviewSourceRefSpec:
    """
    Logical snapshot of references back to the original source consensus bundle.
    
    IMPORTANT: 
    - These values are NOT runtime filesystem paths.
    - They are bundle-relative artifact references or stable artifact names.
    - Absolute paths (e.g., starting with '/', or containing local user home dirs) 
      are strictly forbidden to ensure contract portability.
    """
    source_consensus_run_id: str
    source_bundle_filename: Optional[str] = None
    source_consensus_manifest_path: Optional[str] = None
    source_consensus_handoff_contract_path: Optional[str] = None
    source_consensus_decisions_json_path: Optional[str] = None
    source_evidence_profiles_json_path: Optional[str] = None

@dataclass(frozen=True)
class ComparatorReviewDecisionRefSpec:
    """Compact handoff row for downstream integration."""
    comparison_id: str
    decision_status: str
    decided_label_key: Optional[str]
    decided_label_display: Optional[str]
    triage_status: str
    priority: str
    follow_up_required: bool
    review_note: str
    has_conflict: bool
    has_weak_support: bool
    support_margin: Optional[float]

@dataclass(frozen=True)
class ComparatorReviewHandoffPayload:
    """The formal contract for downstream review handoff."""
    schema_name: str = "comparator-review-handoff"
    schema_version: str = "1.0.0"
    generated_at: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    review_run_id: str = ""
    source_consensus_run_id: str = ""
    bundle_refs: ComparatorReviewBundleRefSpec = field(default=None)
    source_refs: ComparatorReviewSourceRefSpec = field(default=None)
    included_comparison_ids: Tuple[str, ...] = field(default_factory=tuple)
    review_decision_refs: Tuple[ComparatorReviewDecisionRefSpec, ...] = field(default_factory=tuple)
    summary: Optional[ComparatorReviewSummarySpec] = None
