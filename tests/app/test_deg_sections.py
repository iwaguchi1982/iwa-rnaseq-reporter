import pytest
import streamlit as st
import pandas as pd
from unittest.mock import MagicMock, patch
from iwa_rnaseq_reporter.app.deg_sections import (
    render_deg_comparison_design_section,
    render_deg_analysis_section,
)
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext

def test_render_deg_comparison_design_section_smoke(monkeypatch):
    """
    Smoke test for DEG Comparison Design section with mocked streamlit.
    """
    mock_st = MagicMock()
    monkeypatch.setattr("streamlit.header", mock_st.header)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.subheader", mock_st.subheader)
    monkeypatch.setattr("streamlit.dataframe", mock_st.dataframe)
    monkeypatch.setattr("streamlit.selectbox", lambda label, options, **kwargs: options[0] if options else None)
    monkeypatch.setattr("streamlit.columns", lambda n: [MagicMock() for _ in range(n)])
    monkeypatch.setattr("streamlit.write", mock_st.write)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)
    monkeypatch.setattr("streamlit.success", mock_st.success)
    monkeypatch.setattr("streamlit.expander", MagicMock())

    # Mock Workspace
    mock_workspace = MagicMock(spec=AnalysisWorkspaceContext)
    mock_workspace.dataset = MagicMock()
    mock_workspace.matrix_kind = "gene_tpm"
    mock_workspace.analysis_config = MagicMock()
    mock_workspace.analysis_config.log2p1 = True
    mock_workspace.analysis_config.use_exclude = True
    mock_workspace.analysis_config.min_feature_nonzero_samples = 1
    mock_workspace.analysis_config.min_feature_mean = 0.0

    # Mock legacy functions called inside helper
    with patch("iwa_rnaseq_reporter.app.deg_sections.build_analysis_sample_table") as mock_build_ans:
        # v0.1.4: summarize_groups expects 'analysis_included' column
        mock_build_ans.return_value = pd.DataFrame({
            "sample_id": ["S1", "S2", "S3", "S4", "S5", "S6"], 
            "group": ["A", "A", "A", "B", "B", "B"],
            "analysis_included": [True] * 6
        })
        
        with patch("iwa_rnaseq_reporter.app.deg_sections.get_comparison_candidate_columns", return_value=["group"]):
            with patch("iwa_rnaseq_reporter.app.deg_sections.summarize_groups") as mock_sum_groups:
                mock_sum_groups.return_value = pd.DataFrame({"group_name": ["A", "B"], "sample_count": [3, 3]})
            
            with patch("iwa_rnaseq_reporter.app.deg_sections.build_deg_input") as mock_build_deg:
                mock_deg_input = MagicMock()
                mock_deg_input.feature_matrix = pd.DataFrame(columns=["S1", "S2", "S3", "S4", "S5", "S6"])
                mock_deg_input.group_a_samples = ["S1", "S2", "S3"]
                mock_deg_input.group_b_samples = ["S4", "S5", "S6"]
                mock_build_deg.return_value = mock_deg_input
                
                with patch("iwa_rnaseq_reporter.app.deg_sections.validate_deg_input", return_value=[]):
                    with patch("iwa_rnaseq_reporter.app.deg_sections.build_comparison_sample_table", return_value=pd.DataFrame()):
                        
                        deg_input, col, g_a, g_b = render_deg_comparison_design_section(mock_workspace)
                        
                        assert deg_input == mock_deg_input
                        assert col == "group"
                        assert g_a == "A"
                        assert g_b == "B"
                        assert mock_st.header.called


def test_render_deg_analysis_section_smoke(monkeypatch):
    """
    Smoke test for DEG Analysis section with mocked streamlit and session_state.
    """
    mock_st = MagicMock()
    monkeypatch.setattr("streamlit.header", mock_st.header)
    monkeypatch.setattr("streamlit.subheader", mock_st.subheader)
    monkeypatch.setattr("streamlit.markdown", mock_st.markdown)
    monkeypatch.setattr("streamlit.button", lambda label, **kwargs: False)
    monkeypatch.setattr("streamlit.columns", lambda n: [MagicMock() for _ in range(n)])
    monkeypatch.setattr("streamlit.number_input", lambda label, **kwargs: 0.05)
    monkeypatch.setattr("streamlit.selectbox", lambda label, options, **kwargs: options[0])
    monkeypatch.setattr("streamlit.dataframe", mock_st.dataframe)
    monkeypatch.setattr("streamlit.info", mock_st.info)
    monkeypatch.setattr("streamlit.metric", mock_st.metric)
    monkeypatch.setattr("streamlit.plotly_chart", mock_st.plotly_chart)
    monkeypatch.setattr("streamlit.caption", mock_st.caption)
    monkeypatch.setattr("streamlit.download_button", mock_st.download_button)
    monkeypatch.setattr("streamlit.write", mock_st.write)
    monkeypatch.setattr("streamlit.error", mock_st.error)
    monkeypatch.setattr("streamlit.warning", mock_st.warning)

    # Mock Workspace
    mock_workspace = MagicMock(spec=AnalysisWorkspaceContext)
    mock_workspace.matrix_kind = "gene_tpm"
    mock_workspace.analysis_config = MagicMock()
    mock_workspace.analysis_config.log2p1 = True
    mock_workspace.analysis_config.use_exclude = True
    mock_workspace.analysis_config.min_feature_nonzero_samples = 1
    mock_workspace.analysis_config.min_feature_mean = 0.0
    mock_workspace.dataset = MagicMock()
    mock_workspace.dataset.feature_annotation = pd.DataFrame()

    # Mock DegInput and DegResult
    mock_deg_input = MagicMock()
    mock_deg_input.group_a_samples = ["S1"]
    mock_deg_input.group_b_samples = ["S2"]

    # SessionStateProxy supports both dict-like and attribute-like access.
    # Standard dict doesn't support .deg_res, so we use MagicMock.
    mock_session_state = MagicMock()
    mock_deg_res = MagicMock()
    mock_session_state.deg_res = mock_deg_res
    mock_session_state.__contains__.side_effect = lambda k: k == "deg_res"
    monkeypatch.setattr("streamlit.session_state", mock_session_state)

    mock_deg_res.group_a = "A"
    mock_deg_res.group_b = "B"
    mock_deg_res.n_features_tested = 100
    mock_deg_res.result_table = pd.DataFrame({
        "feature_id": ["G1"],
        "display_label": ["G1_label"],
        "log2_fc": [2.0],
        "padj": [0.01],
        "abs_log2_fc": [2.0]
    })

    with patch("iwa_rnaseq_reporter.app.deg_sections.add_display_labels", side_effect=lambda df, ann: df):
        render_deg_analysis_section(
            mock_workspace, mock_deg_input, "group", "A", "B"
        )
        
        # If this fails, check mock_st.error.call_args_list to see the exception
        assert not mock_st.error.called, f"Unexpected error: {mock_st.error.call_args_list}"
        assert mock_st.header.called
        assert mock_st.plotly_chart.called
