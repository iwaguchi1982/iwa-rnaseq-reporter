import pytest
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonRecord, ComparisonPortfolioContext

def test_comparison_portfolio_context_basic():
    """
    Verify basic properties of ComparisonPortfolioContext.
    """
    portfolio = ComparisonPortfolioContext(portfolio_id="test-p")
    assert portfolio.portfolio_id == "test-p"
    assert portfolio.count == 0
    assert portfolio.comparison_ids == []

def test_comparison_record_structure():
    """
    Verify ComparisonRecord can be instantiated (lightweight check).
    """
    # Just checking field presence as it's a frozen dataclass
    record = ComparisonRecord(
        comparison_id="id1",
        comparison_label="label",
        export_payload=None,
        handoff_payload=None,
        bundle_filename="file.zip",
        summary_metrics=None
    )
    assert record.comparison_id == "id1"
