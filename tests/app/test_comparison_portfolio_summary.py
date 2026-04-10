import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_summary import (
    build_comparison_portfolio_summary_row,
    build_comparison_portfolio_summary_rows,
    build_comparison_portfolio_summary_dataframe
)
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonRecord

def test_build_summary_row_success():
    """
    Verify summary row extraction from a complex record.
    """
    mock_record = MagicMock()
    mock_record.comparison_id = "id1"
    mock_record.comparison_label = "label1"
    
    # Metadata
    mock_record.export_payload = MagicMock()
    mock_record.export_payload.metadata = MagicMock()
    mock_record.export_payload.metadata.matrix_kind = "gene_tpm"
    
    # Metrics
    mock_record.summary_metrics = MagicMock()
    mock_record.summary_metrics.n_features_tested = 100
    mock_record.summary_metrics.n_sig_up = 10
    mock_record.summary_metrics.n_sig_down = 5
    mock_record.summary_metrics.max_abs_log2_fc = 4.2
    
    row = build_comparison_portfolio_summary_row(mock_record)
    
    assert row.comparison_id == "id1"
    assert row.matrix_kind == "gene_tpm"
    assert row.n_sig_up == 10
    assert row.max_abs_log2_fc == 4.2

def test_build_summary_dataframe_empty():
    """
    Verify safe conversion with no records.
    """
    df = build_comparison_portfolio_summary_dataframe([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert "comparison_id" in df.columns

def test_build_summary_dataframe_with_data():
    """
    Verify dataframe content.
    """
    mock_row = MagicMock()
    mock_row.comparison_id = "id1"
    # To use vars(r), the mock needs to behave like a dataclass or we use real objects
    from iwa_rnaseq_reporter.app.comparison_portfolio_summary import ComparisonPortfolioSummaryRow
    row = ComparisonPortfolioSummaryRow("id1", "lab", "kind", 100, 10, 5, 2.0)
    
    df = build_comparison_portfolio_summary_dataframe([row])
    assert len(df) == 1
    assert df.iloc[0]["comparison_id"] == "id1"
    assert df.iloc[0]["n_sig_up"] == 10
