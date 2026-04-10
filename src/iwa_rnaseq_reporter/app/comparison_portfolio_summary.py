from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
from .comparison_portfolio_context import ComparisonRecord, ComparisonPortfolioContext

@dataclass(frozen=True)
class ComparisonPortfolioSummaryRow:
    """
    Flat read-side representation of a comparison record for UI tables.
    """
    comparison_id: str
    comparison_label: str
    matrix_kind: str
    n_features_tested: int
    n_sig_up: int
    n_sig_down: int
    max_abs_log2_fc: Optional[float]

def build_comparison_portfolio_summary_row(record: ComparisonRecord) -> ComparisonPortfolioSummaryRow:
    """
    Extract summary information from a typed ComparisonRecord.
    """
    m = record.summary_metrics
    # matrix_kind is in export_payload.metadata
    matrix_kind = record.export_payload.metadata.matrix_kind
    
    return ComparisonPortfolioSummaryRow(
        comparison_id=record.comparison_id,
        comparison_label=record.comparison_label,
        matrix_kind=matrix_kind,
        n_features_tested=m.n_features_tested,
        n_sig_up=m.n_sig_up,
        n_sig_down=m.n_sig_down,
        max_abs_log2_fc=m.max_abs_log2_fc
    )

def build_comparison_portfolio_summary_rows(portfolio: ComparisonPortfolioContext) -> List[ComparisonPortfolioSummaryRow]:
    """
    Convert all records in a portfolio to summary rows.
    """
    return [build_comparison_portfolio_summary_row(r) for r in portfolio.records]

def build_comparison_portfolio_summary_dataframe(rows: List[ComparisonPortfolioSummaryRow]) -> pd.DataFrame:
    """
    Convert summary rows to a pandas DataFrame for UI table display.
    """
    if not rows:
        return pd.DataFrame(columns=[
            "comparison_id", "comparison_label", "matrix_kind", 
            "n_features_tested", "n_sig_up", "n_sig_down", "max_abs_log2_fc"
        ])
    
    return pd.DataFrame([vars(r) for r in rows])
