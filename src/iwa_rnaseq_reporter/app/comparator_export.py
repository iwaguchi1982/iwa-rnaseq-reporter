from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparator_engine import ComparatorSkippedMatchSpec, ComparatorEngineIssueSpec, ComparatorResultSummarySpec

@dataclass(frozen=True)
class ComparatorExportManifestSpec:
    """
    Identity and high-level summary of the comparison engine run.
    """
    comparator_run_id: str
    portfolio_id: str
    n_total_matches_requested: int
    n_successful_matches: int
    n_skipped_matches: int

@dataclass(frozen=True)
class ComparatorExportMatchRowSpec:
    """
    Flattened version of a match result for tabular export (CSV) and easy parsing.
    """
    comparison_id: str
    reference_dataset_id: str
    reference_comparison_id: str
    n_overlap_features: int
    n_top_n_overlap_features: int
    direction_concordance: Optional[float]
    signed_effect_correlation: Optional[float]

@dataclass(frozen=True)
class ComparatorExportPayload:
    """
    Intermediate consolidation of all results for bundle formatting.
    """
    manifest: ComparatorExportManifestSpec
    match_rows: Tuple[ComparatorExportMatchRowSpec, ...]
    skipped_matches: Tuple[ComparatorSkippedMatchSpec, ...]
    issues: Tuple[ComparatorEngineIssueSpec, ...]
    summary: ComparatorResultSummarySpec
