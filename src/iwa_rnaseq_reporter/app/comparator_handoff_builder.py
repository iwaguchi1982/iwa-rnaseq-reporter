from typing import Tuple, Set
from .comparator_engine import ComparatorResultContext
from .comparator_export import ComparatorExportPayload
from .comparator_handoff import (
    ComparatorHandoffPayload,
    ComparatorBundleRefSpec,
    ComparatorIncludedComparisonResultRefSpec
)

def build_comparator_handoff_payload(
    result_context: ComparatorResultContext,
    export_payload: ComparatorExportPayload,
    comparator_bundle_filename: str
) -> ComparatorHandoffPayload:
    """
    Construct the official handoff contract for the comparison results.
    """
    manifest = export_payload.manifest
    run_id = manifest.comparator_run_id
    portfolio_id = manifest.portfolio_id
    
    # 1. Distinct reference datasets that had successful matches
    successful_dataset_ids: Set[str] = {
        res.reference_dataset_id for res in result_context.match_results
    }
    
    # 2. Per-comparison result summaries
    comparison_ids = result_context.matching_context.summary.accepted_comparison_ids
    result_refs = []
    
    for cid in comparison_ids:
        n_success = sum(1 for r in result_context.match_results if r.comparison_id == cid)
        n_skipped = sum(1 for s in result_context.skipped_matches if s.comparison_id == cid)
        
        result_refs.append(ComparatorIncludedComparisonResultRefSpec(
            comparison_id=cid,
            n_successful_matches=n_success,
            n_skipped_matches=n_skipped
        ))
        
    return ComparatorHandoffPayload(
        comparator_run_id=run_id,
        portfolio_id=portfolio_id,
        bundle_refs=ComparatorBundleRefSpec(comparator_bundle_filename),
        included_comparison_ids=tuple(comparison_ids),
        included_reference_dataset_ids=tuple(sorted(successful_dataset_ids)),
        comparison_result_refs=tuple(result_refs),
        summary=result_context.summary
    )
