from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class ComparisonPortfolioBundleRefSpec:
    """
    References to key orchestration files within the portfolio bundle.
    """
    portfolio_bundle_filename: str
    portfolio_manifest_path: str = "portfolio_manifest.json"
    comparison_index_path: str = "comparison_index.json"
    portfolio_handoff_contract_path: str = "portfolio_handoff_contract.json"


@dataclass(frozen=True)
class ComparisonPortfolioIncludedComparisonRefSpec:
    """
    References to individual comparison artifacts within the bundle.
    Paths must be relative to the bundle root.
    """
    comparison_id: str
    comparison_label: str
    matrix_kind: str
    handoff_contract_path: str
    comparison_summary_path: str
    summary_metrics_path: str


@dataclass(frozen=True)
class ComparisonPortfolioFeatureIdSystemSummarySpec:
    """
    Summary of feature ID systems used across all comparisons.
    Used by downstream to check prerequisites.
    """
    feature_id_systems: List[str]
    is_mixed: bool


@dataclass(frozen=True)
class ComparisonPortfolioSharedAnalysisConstraintsSpec:
    """
    High-level constraints sharing across the portfolio.
    """
    matrix_kinds: List[str]
    n_comparisons: int


@dataclass(frozen=True)
class ComparisonPortfolioHandoffPayload:
    """
    Formal contract for handing off a multi-comparison portfolio to downstream tools.
    """
    portfolio_id: str
    included_comparison_ids: List[str]
    bundle_refs: ComparisonPortfolioBundleRefSpec
    included_comparisons: List[ComparisonPortfolioIncludedComparisonRefSpec]
    feature_id_system_summary: ComparisonPortfolioFeatureIdSystemSummarySpec
    matrix_kinds: List[str]
    shared_analysis_constraints: ComparisonPortfolioSharedAnalysisConstraintsSpec

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
