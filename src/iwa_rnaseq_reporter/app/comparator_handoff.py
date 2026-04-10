from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any
from .comparator_engine import ComparatorResultSummarySpec

@dataclass(frozen=True)
class ComparatorBundleRefSpec:
    """
    Relative paths to core result files within the comparator bundle.
    """
    comparator_bundle_filename: str
    comparator_manifest_path: str = "comparator_manifest.json"
    comparator_summary_path: str = "comparator_summary.json"
    match_results_path: str = "match_results.json"
    skipped_matches_path: str = "skipped_matches.json"
    comparator_handoff_contract_path: str = "comparator_handoff_contract.json"

@dataclass(frozen=True)
class ComparatorIncludedComparisonResultRefSpec:
    """
    Summary of results specific to an individual experimental comparison.
    """
    comparison_id: str
    n_successful_matches: int
    n_skipped_matches: int

@dataclass(frozen=True)
class ComparatorHandoffPayload:
    """
    Formal contract for handing off comparison results to downstream consumers.
    """
    comparator_run_id: str
    portfolio_id: str
    bundle_refs: ComparatorBundleRefSpec
    included_comparison_ids: Tuple[str, ...]
    included_reference_dataset_ids: Tuple[str, ...]
    comparison_result_refs: Tuple[ComparatorIncludedComparisonResultRefSpec, ...]
    summary: ComparatorResultSummarySpec

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
