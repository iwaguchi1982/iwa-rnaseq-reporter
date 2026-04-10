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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonPortfolioBundleRefSpec":
        return cls(**data)


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonPortfolioIncludedComparisonRefSpec":
        return cls(**data)


@dataclass(frozen=True)
class ComparisonPortfolioFeatureIdSystemSummarySpec:
    """
    Summary of feature ID systems used across all comparisons.
    Used by downstream to check prerequisites.
    """
    feature_id_systems: List[str]
    is_mixed: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonPortfolioFeatureIdSystemSummarySpec":
        return cls(**data)


@dataclass(frozen=True)
class ComparisonPortfolioSharedAnalysisConstraintsSpec:
    """
    High-level constraints sharing across the portfolio.
    """
    matrix_kinds: List[str]
    n_comparisons: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonPortfolioSharedAnalysisConstraintsSpec":
        return cls(**data)


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonPortfolioHandoffPayload":
        bundle_refs = ComparisonPortfolioBundleRefSpec.from_dict(data["bundle_refs"])
        included_comps = [
            ComparisonPortfolioIncludedComparisonRefSpec.from_dict(c) 
            for c in data["included_comparisons"]
        ]
        id_summary = ComparisonPortfolioFeatureIdSystemSummarySpec.from_dict(data["feature_id_system_summary"])
        constraints = ComparisonPortfolioSharedAnalysisConstraintsSpec.from_dict(data["shared_analysis_constraints"])
        
        return cls(
            portfolio_id=data["portfolio_id"],
            included_comparison_ids=data["included_comparison_ids"],
            bundle_refs=bundle_refs,
            included_comparisons=included_comps,
            feature_id_system_summary=id_summary,
            matrix_kinds=data["matrix_kinds"],
            shared_analysis_constraints=constraints
        )
