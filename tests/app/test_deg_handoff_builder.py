import pytest
import pandas as pd
from iwa_rnaseq_reporter.app.deg_handoff_builder import build_deg_handoff_payload
from iwa_rnaseq_reporter.app.deg_export_spec import (
    DegExportPayload,
    DegExportSummarySpec,
    DegExportRunMetadataSpec
)
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

def test_build_deg_handoff_payload_success():
    """
    Verify mapping from DegExportPayload to DegHandoffPayload.
    """
    summary = DegExportSummarySpec("group", "A", "B", "A vs B", 3, 3)
    metadata = DegExportRunMetadataSpec("gene_tpm", True, True, 1, 0.0, 0.05, 1.0, "padj", 50)
    metrics = DegSummaryMetrics(100, 10, 5, 5.0)
    result_table = pd.DataFrame({"G1": [1]})
    
    export_payload = DegExportPayload(summary, metadata, result_table, metrics)
    
    handoff = build_deg_handoff_payload(export_payload, "bundle.zip")
    
    assert handoff.identity.comparison_column == "group"
    assert handoff.identity.comparison_id == "group__A__vs__B__gene_tpm"
    assert handoff.artifact_refs.bundle_filename == "bundle.zip"
    assert handoff.analysis_metadata["padj_threshold"] == 0.05
    assert handoff.summary_metrics["n_sig_up"] == 10
