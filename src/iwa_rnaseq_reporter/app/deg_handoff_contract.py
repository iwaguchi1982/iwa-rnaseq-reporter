from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import re

def build_deg_comparison_id(comparison_column: str, group_a: str, group_b: str, matrix_kind: str) -> str:
    """
    Generate a deterministic, human-readable ID for a DEG comparison.
    """
    raw = f"{comparison_column}__{group_a}__vs__{group_b}__{matrix_kind}"
    # Sanitize: only alphanumeric and underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    # Collapse multiple underscores
    sanitized = re.sub(r"__+", "__", sanitized)
    return sanitized

@dataclass(frozen=True)
class DegHandoffIdentitySpec:
    """
    Identity of the comparison for tracking across systems.
    """
    comparison_id: str
    comparison_label: str
    comparison_column: str
    group_a: str
    group_b: str

@dataclass(frozen=True)
class DegHandoffDataRefSpec:
    """
    Official filenames within the export bundle for reliable downstream access.
    """
    bundle_filename: str
    result_table_filename: str = "deg_results.csv"
    comparison_summary_filename: str = "comparison_summary.json"
    run_metadata_filename: str = "run_metadata.json"
    summary_metrics_filename: str = "summary_metrics.json"
    report_summary_filename: str = "report_summary.md"
    handoff_contract_filename: str = "handoff_contract.json"

@dataclass(frozen=True)
class DegHandoffPayload:
    """
    Formal contract for handing off DEG results to downstream modules.
    Lightweight and pointer-heavy rather than containing full result tables.
    """
    identity: DegHandoffIdentitySpec
    analysis_metadata: Dict[str, Any]  # Snapshot from DegExportRunMetadataSpec
    artifact_refs: DegHandoffDataRefSpec
    summary_metrics: Dict[str, Any]    # Snapshot from DegSummaryMetrics
    feature_id_system: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
