import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from iwa_rnaseq_reporter.app.deg_result_builder import build_deg_result_context
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig

def test_build_deg_result_context_success():
    """
    Verify that build_deg_result_context correctly processes results.
    """
    # 1. Mocks
    mock_workspace = MagicMock()
    mock_workspace.matrix_kind = "gene_tpm"
    mock_workspace.analysis_config = AnalysisConfig("gene_tpm", True, True, 1, 0.0)
    mock_workspace.dataset = MagicMock()
    mock_workspace.dataset.feature_annotation = pd.DataFrame()

    mock_deg_res = MagicMock()
    mock_deg_res.n_features_tested = 100
    mock_deg_res.result_table = pd.DataFrame({
        "feature_id": ["G1", "G2"],
        "log2_fc": [2.0, -2.0],
        "padj": [0.01, 0.01],
        "abs_log2_fc": [2.0, 2.0]
    })

    # 2. Call builder
    # Mock add_display_labels to avoid complex logic in unit test
    with patch("iwa_rnaseq_reporter.app.deg_result_builder.add_display_labels", side_effect=lambda df, ann: df):
        context = build_deg_result_context(
            workspace=mock_workspace,
            deg_input_obj=None,
            comparison_column="group",
            group_a="A",
            group_b="B",
            deg_res=mock_deg_res,
            p_thresh=0.05,
            fc_thresh=1.0,
            sort_by="padj",
            top_n=10
        )

    # 3. Assertions
    assert context.comparison_column == "group"
    assert context.group_a == "A"
    assert context.group_b == "B"
    assert context.summary_metrics.n_sig_up == 1
    assert context.summary_metrics.n_sig_down == 1
    assert context.summary_metrics.max_abs_log2_fc == 2.0
    assert "log2_fc" in context.result_table.columns
    assert context.threshold_snapshot.padj_threshold == 0.05
