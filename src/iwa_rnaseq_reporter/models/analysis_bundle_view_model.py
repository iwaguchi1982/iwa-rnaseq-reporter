from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class ReporterAnalysisBundle:
    """
    Reporter-side view model for an Analysis Bundle.
    This model represents the safe, public surface area of the bundle
    as defined in the Handoff Profile (v0.12).
    """
    # Identification
    run_id: str
    matrix_id: str
    
    # Bundle Manifest
    analysis_bundle_manifest_path: str
    
    # Contract/Metadata
    contract_name: str
    contract_version: str
    bundle_kind: str
    producer: str
    producer_version: str
    
    # Matrix Specs
    matrix_shape: Dict[str, int]
    sample_axis: str
    feature_id_system: str
    column_order_specimen_ids: List[str]
    
    # Status & Descriptors (Optional/Nullable)
    source_quantifier_summary: Dict[str, Any] = field(default_factory=dict)
    feature_annotation_status: Optional[Dict[str, Any]] = None
    sample_metadata_alignment_status: Optional[Dict[str, Any]] = None
    warning_summary: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Basic validation/normalization if needed on the reporter side
        pass
