import pytest
import uuid
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_builder import (
    build_comparison_record,
    build_empty_comparison_portfolio_context,
    upsert_comparison_record,
    list_comparison_records
)
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonRecord, ComparisonPortfolioContext

def test_build_empty_portfolio():
    portfolio = build_empty_comparison_portfolio_context()
    assert isinstance(portfolio.portfolio_id, str)
    assert len(portfolio.records) == 0

def test_build_comparison_record_success():
    mock_context = MagicMock()
    mock_context.comparison_label = "A vs B"
    mock_context.summary_metrics = MagicMock()
    
    mock_export = MagicMock()
    mock_handoff = MagicMock()
    mock_handoff.identity.comparison_id = "comp_1"
    
    record = build_comparison_record(mock_context, mock_export, mock_handoff, "bundle.zip")
    
    assert record.comparison_id == "comp_1"
    assert record.comparison_label == "A vs B"
    assert record.bundle_filename == "bundle.zip"

def test_build_comparison_record_failure():
    mock_handoff = MagicMock()
    mock_handoff.identity.comparison_id = "" # Empty ID
    
    with pytest.raises(ValueError, match="comparison_id is missing"):
        build_comparison_record(MagicMock(), MagicMock(), mock_handoff, "file.zip")

def test_upsert_comparison_record_logic():
    p = build_empty_comparison_portfolio_context("p1")
    
    # 1. First insert
    r1 = MagicMock(spec=ComparisonRecord)
    r1.comparison_id = "id1"
    r1.comparison_label = "L1"
    
    p = upsert_comparison_record(p, r1)
    assert p.count == 1
    assert p.records[0].comparison_id == "id1"
    
    # 2. Second insert (different ID)
    r2 = MagicMock(spec=ComparisonRecord)
    r2.comparison_id = "id2"
    p = upsert_comparison_record(p, r2)
    assert p.count == 2
    
    # 3. Third insert (same as first ID - UPSERT)
    r1_v2 = MagicMock(spec=ComparisonRecord)
    r1_v2.comparison_id = "id1"
    r1_v2.comparison_label = "L1 Updated"
    
    p = upsert_comparison_record(p, r1_v2)
    assert p.count == 2 # Still 2
    assert p.records[0].comparison_label == "L1 Updated" # Updated in place
    assert p.records[1].comparison_id == "id2" # Order maintained
