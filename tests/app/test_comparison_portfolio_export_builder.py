import pytest
import io
import zipfile
import json
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonPortfolioContext, ComparisonRecord
from iwa_rnaseq_reporter.app.comparison_portfolio_export_builder import (
    build_comparison_portfolio_export_payload,
    build_comparison_portfolio_export_bundle,
    build_comparison_portfolio_bundle_filename
)

from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

def test_build_portfolio_export_payload_success():
    mock_p = MagicMock()
    mock_p.portfolio_id = "p1"
    mock_p.count = 1
    mock_p.comparison_ids = ["c1"]
    
    mock_record = MagicMock()
    mock_record.comparison_id = "c1"
    mock_record.comparison_label = "L1"
    mock_record.bundle_filename = "b1.zip"
    
    # Nested metadata mock
    mock_record.export_payload = MagicMock()
    mock_record.export_payload.metadata = MagicMock()
    mock_record.export_payload.metadata.matrix_kind = "gene_tpm"
    mock_record.export_payload.result_table = pd.DataFrame({"feature_id": [], "log2_fc": [], "padj": []})
    
    # Real metrics instance to support asdict()
    mock_record.summary_metrics = DegSummaryMetrics(100, 10, 5, 3.0)
    
    mock_p.records = [mock_record]
    
    payload = build_comparison_portfolio_export_payload(mock_p)
    assert payload.manifest.portfolio_id == "p1"
    assert len(payload.comparison_index) == 1
    assert payload.comparison_index[0].comparison_id == "c1"
    assert payload.comparison_index[0].n_sig_up == 10

def test_build_portfolio_export_payload_empty():
    mock_p = MagicMock()
    mock_p.count = 0
    with pytest.raises(ValueError, match="empty portfolio"):
        build_comparison_portfolio_export_payload(mock_p)

def test_build_portfolio_export_bundle_contents():
    mock_p = MagicMock()
    mock_p.portfolio_id = "p-test"
    mock_p.count = 1
    mock_p.comparison_ids = ["comp-1"]
    
    rec = MagicMock()
    rec.comparison_id = "comp-1"
    rec.comparison_label = "Label1"
    rec.bundle_filename = "single_comp.zip"
    
    exp = MagicMock()
    exp.metadata.to_dict.return_value = {"matrix_kind": "gene_tpm"}
    exp.metadata.matrix_kind = "gene_tpm"
    exp.metadata.log2p1 = True
    exp.metadata.use_exclude = True
    exp.metadata.min_feature_nonzero_samples = 1
    exp.metadata.min_feature_mean = 0.0
    exp.metadata.padj_threshold = 0.05
    exp.metadata.abs_log2_fc_threshold = 1.0
    
    exp.summary.to_dict.return_value = {"comparison_label": "Label1"}
    exp.summary.comparison_label = "Label1"
    exp.summary.comparison_column = "col"
    exp.summary.group_a = "A"
    exp.summary.sample_count_group_a = 3
    exp.summary.group_b = "B"
    exp.summary.sample_count_group_b = 3
    exp.result_table = pd.DataFrame({"feature_id": ["G1"], "log2_fc": [1.0], "padj": [0.01]})
    
    # Use real dataclass for asdict support
    real_metrics = DegSummaryMetrics(100, 10, 5, 4.0)
    exp.summary_metrics = real_metrics
    rec.export_payload = exp
    rec.summary_metrics = real_metrics
    rec.handoff_payload = MagicMock()
    rec.handoff_payload.feature_id_system = "ENSEMBL"
    rec.handoff_payload.to_dict.return_value = {"id": "comp-1", "feature_id_system": "ENSEMBL"}
    
    mock_p.records = [rec]
    
    # Generate bundle
    zip_bytes = build_comparison_portfolio_export_bundle(mock_p)
    assert isinstance(zip_bytes, bytes)
    
    # Inspect ZIP
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        file_list = zf.namelist()
        assert "portfolio_manifest.json" in file_list
        assert "comparison_index.json" in file_list
        assert "comparisons/comp-1/handoff_contract.json" in file_list
        assert "comparisons/comp-1/comparison_summary.json" in file_list
        assert "comparisons/comp-1/report_summary.md" in file_list
        assert "comparisons/comp-1/deg_results.csv" in file_list
        
        # Verify JSON content
        manifest = json.loads(zf.read("portfolio_manifest.json"))
        assert manifest["portfolio_id"] == "p-test"
        
        index = json.loads(zf.read("comparison_index.json"))
        assert len(index) == 1
        assert index[0]["comparison_id"] == "comp-1"
