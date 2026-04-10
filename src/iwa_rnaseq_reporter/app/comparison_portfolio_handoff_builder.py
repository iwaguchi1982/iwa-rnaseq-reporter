from typing import List, Set
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonPortfolioContext
from .comparison_portfolio_export import ComparisonPortfolioExportPayload
from .comparison_portfolio_handoff import (
    ComparisonPortfolioHandoffPayload,
    ComparisonPortfolioBundleRefSpec,
    ComparisonPortfolioIncludedComparisonRefSpec,
    ComparisonPortfolioFeatureIdSystemSummarySpec,
    ComparisonPortfolioSharedAnalysisConstraintsSpec
)

def build_comparison_portfolio_handoff_payload(
    portfolio: ComparisonPortfolioContext,
    export_payload: ComparisonPortfolioExportPayload,
    portfolio_bundle_filename: str
) -> ComparisonPortfolioHandoffPayload:
    """
    Build the formal handoff contract for the given portfolio.
    """
    if portfolio.count == 0:
        raise ValueError("Cannot build handoff contract for an empty portfolio.")

    # 1. Bundle Refs
    bundle_refs = ComparisonPortfolioBundleRefSpec(
        portfolio_bundle_filename=portfolio_bundle_filename
    )

    # 2. Included Comparison Refs
    included_comparisons = []
    for record in portfolio.records:
        cid = record.comparison_id
        base_path = f"comparisons/{cid}"
        
        included_comparisons.append(ComparisonPortfolioIncludedComparisonRefSpec(
            comparison_id=cid,
            comparison_label=record.comparison_label,
            matrix_kind=record.export_payload.metadata.matrix_kind,
            handoff_contract_path=f"{base_path}/handoff_contract.json",
            comparison_summary_path=f"{base_path}/comparison_summary.json",
            summary_metrics_path=f"{base_path}/summary_metrics.json"
        ))

    # 3. Feature ID System Summary
    systems: Set[str] = set()
    for record in portfolio.records:
        sys = record.handoff_payload.feature_id_system
        if sys:
            systems.add(sys)
        else:
            systems.add("unknown")
            
    id_summary = ComparisonPortfolioFeatureIdSystemSummarySpec(
        feature_id_systems=list(sorted(list(systems))),
        is_mixed=len(systems) > 1
    )

    # 4. Matrix Kinds
    matrix_kinds = list(sorted(list(set(
        record.export_payload.metadata.matrix_kind for record in portfolio.records
    ))))

    # 5. Constraints
    constraints = ComparisonPortfolioSharedAnalysisConstraintsSpec(
        matrix_kinds=matrix_kinds,
        n_comparisons=portfolio.count
    )

    return ComparisonPortfolioHandoffPayload(
        portfolio_id=portfolio.portfolio_id,
        included_comparison_ids=portfolio.comparison_ids,
        bundle_refs=bundle_refs,
        included_comparisons=included_comparisons,
        feature_id_system_summary=id_summary,
        matrix_kinds=matrix_kinds,
        shared_analysis_constraints=constraints
    )
