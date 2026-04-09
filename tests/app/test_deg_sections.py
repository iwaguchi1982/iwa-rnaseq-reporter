import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.deg_sections import render_deg_comparison_design_section
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

from unittest.mock import patch
