import pytest
import io
import zipfile
import json
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonPortfolioContext
from iwa_rnaseq_reporter.app.comparison_portfolio_export import ComparisonPortfolioExportPayload
from iwa_rnaseq_reporter.app.comparison_portfolio_handoff_builder import build_comparison_portfolio_handoff_payload

def test_build_portfolio_handoff_payload_consistency():
    # 1. Setup Portfolio with mixed ID systems
    mock_p = MagicMock()
    mock_p.portfolio_id = "p-handoff"
    mock_p.count = 2
    mock_p.comparison_ids = ["c1", "c2"]
    
    r1 = MagicMock()
    r1.comparison_id = "c1"
    r1.comparison_label = "L1"
    r1.export_payload.metadata.matrix_kind = "gene_tpm"
    r1.handoff_payload.feature_id_system = "ENSEMBL"
    
    r2 = MagicMock()
    r2.comparison_id = "c2"
    r2.comparison_label = "L2"
    r2.export_payload.metadata.matrix_kind = "gene_tpm"
    r2.handoff_payload.feature_id_system = "SYMBOL"
    
    mock_p.records = [r1, r2]
    
    # 2. Mock Export Payload (already tested in v0.16.3)
    mock_exp = MagicMock(spec=ComparisonPortfolioExportPayload)
    
    # 3. Build Contract
    payload = build_comparison_portfolio_handoff_payload(mock_p, mock_exp, "bundle.zip")
    
    assert payload.portfolio_id == "p-handoff"
    assert len(payload.included_comparisons) == 2
    assert payload.bundle_refs.portfolio_bundle_filename == "bundle.zip"
    
    # Check ID System aggregation
    id_sum = payload.feature_id_system_summary
    assert id_sum.is_mixed is True
    assert "ENSEMBL" in id_sum.feature_id_systems
    assert "SYMBOL" in id_sum.feature_id_systems
    
    # Check matrix kinds aggregation
    assert payload.matrix_kinds == ["gene_tpm"]
    assert payload.shared_analysis_constraints.n_comparisons == 2

def test_build_portfolio_handoff_payload_empty():
    mock_p = MagicMock()
    mock_p.count = 0
    with pytest.raises(ValueError, match="empty portfolio"):
        build_comparison_portfolio_handoff_payload(mock_p, MagicMock(), "b.zip")
