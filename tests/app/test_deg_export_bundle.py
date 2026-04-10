import pytest
import io
import zipfile
import json
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.deg_export_bundle import (
    build_deg_export_bundle,
    build_deg_export_bundle_filename
)
from iwa_rnaseq_reporter.app.deg_export_spec import (
    DegExportPayload,
    DegExportSummarySpec,
    DegExportRunMetadataSpec
)
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

def test_build_deg_export_bundle_filename():
    """
    Verify filename generation and sanitization.
    """
    mock_payload = MagicMock()
    mock_payload.summary = MagicMock()
    mock_payload.summary.group_a = "Case/1"
    mock_payload.summary.group_b = "Control 2"
    
    filename = build_deg_export_bundle_filename(mock_payload)
    # "/" and " " should be underscores
    assert filename == "deg_bundle_Case_1_vs_Control_2.zip"

def test_build_deg_export_bundle_contents():
    """
    Verify that the ZIP bundle contains all expected files with correct format.
    """
    # 1. Setup Mock Payload
    summary = DegExportSummarySpec("group", "A", "B", "A vs B", 3, 3)
    metadata = DegExportRunMetadataSpec("gene_tpm", True, True, 1, 0.0, 0.05, 1.0, "padj", 50)
    metrics = DegSummaryMetrics(100, 10, 5, 5.0)
    result_table = pd.DataFrame({"feature_id": ["G1"], "log2_fc": [2.0], "padj": [0.01]})
    
    payload = DegExportPayload(summary, metadata, result_table, metrics)
    
    # 2. Build Bundle
    zip_bytes = build_deg_export_bundle(payload)
    assert isinstance(zip_bytes, bytes)
    
    # 3. Inspect ZIP
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        file_list = zf.namelist()
        assert "deg_results.csv" in file_list
        assert "comparison_summary.json" in file_list
        assert "summary_metrics.json" in file_list
        assert "report_summary.md" in file_list
        
        # Verify Handoff Contract JSON
        assert "handoff_contract.json" in file_list
        handoff_json = json.loads(zf.read("handoff_contract.json"))
        assert handoff_json["identity"]["comparison_id"] == "group__A__vs__B__gene_tpm"
        
        # Verify JSON
        meta_json = json.loads(zf.read("run_metadata.json"))
        assert meta_json["matrix_kind"] == "gene_tpm"
        
        # Verify CSV
        csv_text = zf.read("deg_results.csv").decode("utf-8")
        assert "feature_id,log2_fc,padj" in csv_text
        
        # Verify Markdown
        md_text = zf.read("report_summary.md").decode("utf-8")
        assert "# DEG Analysis Report Summary" in md_text
        assert "**Group A (Case)**: A (n=3)" in md_text
