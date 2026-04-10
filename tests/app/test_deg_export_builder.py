import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.deg_export_builder import build_deg_export_payload
from iwa_rnaseq_reporter.app.deg_result_context import (
    DegResultContext,
    DegThresholdSnapshot,
    DegSummaryMetrics
)
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig

def test_build_deg_export_payload_success():
    """
    Verify mapping from DegResultContext to DegExportPayload.
    """
    # 1. Setup Context
    config = AnalysisConfig("gene_tpm", True, True, 1, 0.0)
    thresh = DegThresholdSnapshot(0.05, 1.0, "padj", 100)
    metrics = DegSummaryMetrics(100, 10, 5, 5.0)
    
    mock_context = DegResultContext(
        comparison_column="group",
        group_a="A",
        group_b="B",
        matrix_kind="gene_tpm",
        analysis_config_snapshot=config,
        deg_result=None,
        result_table=pd.DataFrame({"feature_id": ["G1"]}),
        summary_metrics=metrics,
        threshold_snapshot=thresh
    )
    
    # 2. Setup mock deg_input_obj
    mock_deg_input = MagicMock()
    mock_deg_input.group_a_samples = ["S1", "S2"]
    mock_deg_input.group_b_samples = ["S3"]
    
    # 3. Build
    payload = build_deg_export_payload(mock_context, mock_deg_input)
    
    # 4. Assert
    assert payload.summary.comparison_column == "group"
    assert payload.summary.sample_count_group_a == 2
    assert payload.summary.sample_count_group_b == 1
    assert payload.metadata.matrix_kind == "gene_tpm"
    assert payload.metadata.padj_threshold == 0.05
    assert payload.summary_metrics.n_sig_up == 10
