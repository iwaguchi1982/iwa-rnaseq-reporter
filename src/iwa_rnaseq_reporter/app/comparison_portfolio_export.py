from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class ComparisonPortfolioManifestSpec:
    """
    Identity and snapshot metadata for the entire portfolio.
    """
    portfolio_id: str
    n_comparisons: int
    included_comparison_ids: List[str]


@dataclass(frozen=True)
class ComparisonPortfolioIndexEntrySpec:
    """
    Entry in the portfolio-wide comparison index (downstream entry point).
    """
    comparison_id: str
    comparison_label: str
    matrix_kind: str
    n_features_tested: int
    n_sig_up: int
    n_sig_down: int
    max_abs_log2_fc: Optional[float]
    bundle_filename: str


@dataclass(frozen=True)
class ComparisonPortfolioExportPayload:
    """
    Payload containing all data required to build a portfolio export bundle.
    """
    manifest: ComparisonPortfolioManifestSpec
    comparison_index: List[ComparisonPortfolioIndexEntrySpec]
