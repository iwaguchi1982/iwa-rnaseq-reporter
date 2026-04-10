import pytest
import io
import zipfile
import json
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonPortfolioContext
from iwa_rnaseq_reporter.app.comparison_portfolio_export_builder import (
    build_comparison_portfolio_export_bundle,
    build_comparison_portfolio_export_payload
)
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics
from iwa_rnaseq_reporter.app.comparator_intake_builder import build_comparator_intake_context_from_bundle

def test_full_intake_flow_success():
    """
    Integration test: 
    1. Create a real ZIP bundle using v0.16 export logic.
    2. Feed it into v0.17 intake builder.
    """
    # Setup a valid portfolio
    mock_p = MagicMock()
    mock_p.portfolio_id = "p-123"
    mock_p.count = 2
    mock_p.comparison_ids = ["comp-A", "comp-B"]
    
    recs = []
    for cid in ["comp-A", "comp-B"]:
        r = MagicMock()
        r.comparison_id = cid
        r.comparison_label = f"Label {cid}"
        r.bundle_filename = f"bundle_{cid}.zip"
        
        exp = MagicMock()
        exp.metadata.matrix_kind = "gene_tpm"
        exp.metadata.to_dict.return_value = {"matrix_kind": "gene_tpm"}
        exp.summary.to_dict.return_value = {"comparison_label": f"Label {cid}", "comparison_column": "col", "group_a": "A", "group_b": "B"}
        exp.result_table = pd.DataFrame({"feature_id": [], "log2_fc": [], "padj": []})
        
        metrics = DegSummaryMetrics(100, 10, 5, 2.0)
        exp.summary_metrics = metrics
        
        r.export_payload = exp
        r.summary_metrics = metrics
        
        h = MagicMock()
        h.feature_id_system = "ENSEMBL"
        h.identity.comparison_id = cid
        h.identity.comparison_label = f"Label {cid}"
        h.to_dict.return_value = {
            "identity": {"comparison_id": cid, "comparison_label": f"Label {cid}", "comparison_column": "col", "group_a": "A", "group_b": "B"},
            "analysis_metadata": {"matrix_kind": "gene_tpm"},
            "artifact_refs": {"bundle_filename": "b.zip", "result_table_filename": "r.csv", "comparison_summary_filename": "s.json", "run_metadata_filename": "m.json", "summary_metrics_filename": "mt.json", "report_summary_filename": "rp.md", "handoff_contract_filename": "h.json"},
            "summary_metrics": {"n_features_tested": 100, "n_sig_up": 10, "n_sig_down": 5, "max_abs_log2_fc": 2.0},
            "feature_id_system": "ENSEMBL"
        }
        r.handoff_payload = h
        recs.append(r)
        
    mock_p.records = recs
    
    # Generate real bundle bytes
    bundle_bytes = build_comparison_portfolio_export_bundle(mock_p)
    
    # Run Intake
    ctx = build_comparator_intake_context_from_bundle(bundle_bytes)
    
    assert ctx.summary.portfolio_id == "p-123"
    assert ctx.summary.n_accepted_comparisons == 2
    assert ctx.summary.is_ready_for_reference_matching is True
    assert ctx.summary.matrix_kinds == ("gene_tpm",)
    assert ctx.summary.feature_id_systems == ("ENSEMBL",)

def test_intake_with_rejected_comparison():
    """
    Test when one comparison has an unknown feature_id_system.
    """
    mock_p = MagicMock()
    mock_p.portfolio_id = "p-reject"
    mock_p.count = 2
    mock_p.comparison_ids = ["c1", "c2"]
    
    recs = []
    # c1: Consistent
    # c2: Unknown ID System -> Should be rejected
    for i, cid in enumerate(["c1", "c2"]):
        r = MagicMock()
        r.comparison_id = cid
        r.comparison_label = f"L{i}"
        r.bundle_filename = f"b{i}.zip"
        exp = MagicMock()
        exp.metadata.matrix_kind = "gene_tpm"
        exp.metadata.to_dict.return_value = {"matrix_kind": "gene_tpm"}
        exp.summary.to_dict.return_value = {"comparison_label": f"L{i}"}
        exp.result_table = pd.DataFrame({"feature_id": [], "log2_fc": [], "padj": []})
        m = DegSummaryMetrics(100, 10, 5, 2.0)
        exp.summary_metrics = m
        r.export_payload = exp
        r.summary_metrics = m
        
        h = MagicMock()
        h.feature_id_system = "ENSEMBL" if cid == "c1" else "unknown"
        h.identity.comparison_id = cid
        h.identity.comparison_label = f"L{i}"
        h.to_dict.return_value = {
            "identity": {
                "comparison_id": cid, 
                "comparison_label": f"L{i}",
                "comparison_column": "col",
                "group_a": "A",
                "group_b": "B"
            },
            "analysis_metadata": {"matrix_kind": "gene_tpm"},
            "artifact_refs": {"bundle_filename": "b.zip", "result_table_filename": "r.csv", "comparison_summary_filename": "s.json", "run_metadata_filename": "m.json", "summary_metrics_filename": "mt.json", "report_summary_filename": "rp.md", "handoff_contract_filename": "h.json"},
            "summary_metrics": vars(m),
            "feature_id_system": h.feature_id_system
        }
        r.handoff_payload = h
        recs.append(r)
    
    mock_p.records = recs
    bundle_bytes = build_comparison_portfolio_export_bundle(mock_p)
    
    ctx = build_comparator_intake_context_from_bundle(bundle_bytes)
    
    assert ctx.summary.n_total_comparisons == 2
    assert ctx.summary.n_accepted_comparisons == 1
    assert ctx.summary.n_rejected_comparisons == 1
    assert ctx.rejected_comparisons[0].comparison_id == "c2"
    assert "UNKNOWN_ID_SYSTEM" in ctx.rejected_comparisons[0].rejection_codes
    # Still ready for matching because the remaining accepted one is consistent
    assert ctx.summary.is_ready_for_reference_matching is True

def test_intake_fails_if_root_contract_missing():
    # Construct a ZIP without portfolio_handoff_contract.json
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("portfolio_manifest.json", "{}")
        zf.writestr("comparison_index.json", "[]")
        
    with pytest.raises(ValueError, match="portfolio_handoff_contract.json is missing"):
        build_comparator_intake_context_from_bundle(buf.getvalue())
