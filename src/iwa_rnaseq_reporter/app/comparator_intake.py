from dataclasses import dataclass, field
from typing import Optional, Tuple
from .comparison_portfolio_handoff import ComparisonPortfolioHandoffPayload

@dataclass(frozen=True)
class ComparatorValidationIssueSpec:
    issue_code: str
    severity: str  # "warning" | "fatal"
    message: str
    comparison_id: Optional[str] = None

@dataclass(frozen=True)
class ComparatorAcceptedComparisonRefSpec:
    comparison_id: str
    comparison_label: str
    matrix_kind: str
    feature_id_system: str
    handoff_contract_path: str

@dataclass(frozen=True)
class ComparatorRejectedComparisonRefSpec:
    comparison_id: str
    comparison_label: str
    matrix_kind: Optional[str]
    feature_id_system: Optional[str]
    handoff_contract_path: Optional[str]
    rejection_codes: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ComparatorIntakeSummarySpec:
    portfolio_id: str
    n_total_comparisons: int
    n_accepted_comparisons: int
    n_rejected_comparisons: int
    matrix_kinds: Tuple[str, ...]
    feature_id_systems: Tuple[str, ...]
    has_mixed_matrix_kinds: bool
    has_mixed_feature_id_systems: bool
    is_ready_for_reference_matching: bool

@dataclass(frozen=True)
class ComparatorIntakeContext:
    portfolio_handoff: ComparisonPortfolioHandoffPayload
    accepted_comparisons: Tuple[ComparatorAcceptedComparisonRefSpec, ...]
    rejected_comparisons: Tuple[ComparatorRejectedComparisonRefSpec, ...]
    issues: Tuple[ComparatorValidationIssueSpec, ...]
    summary: ComparatorIntakeSummarySpec
