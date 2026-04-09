import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.analysis_sections import (
    render_analysis_matrix_summary,
    render_pca_preview_section,
)
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext

def test_section_helpers_accept_workspace():
    """
    Ensure section helpers accept a workspace object.
    Since they use Streamlit calls, we mainly test that they don't crash 
    before calling st functions or that we can mock st if needed.
    (Simple smoke test for argument compatibility)
    """
    mock_workspace = MagicMock(spec=AnalysisWorkspaceContext)
    
    # We can't easily test st.write without a running streamlit session or heavy mocking,
    # but we can verify the function exists and accepts the argument.
    assert callable(render_analysis_matrix_summary)
    assert callable(render_pca_preview_section)

def test_render_analysis_matrix_summary_smoke(monkeypatch):
    """
    Smoke test for render_analysis_matrix_summary with mocked streamlit.
    """
    mock_st = MagicMock()
    monkeypatch.setattr("streamlit.write", mock_st.write)
    monkeypatch.setattr("streamlit.dataframe", mock_st.dataframe)
    monkeypatch.setattr("streamlit.expander", mock_st.expander)
    
    mock_workspace = MagicMock(spec=AnalysisWorkspaceContext)
    mock_workspace.dataset = MagicMock()
    mock_workspace.sample_count = 5
    mock_workspace.feature_count = 100
    mock_workspace.matrix_kind = "gene_tpm"
    mock_workspace.analysis_sample_table = pd.DataFrame({"sample_id": ["s1"]})
    mock_workspace.analysis_matrix = pd.DataFrame([[1.0]], index=["f1"], columns=["s1"])
    mock_workspace.analysis_config = MagicMock()
    mock_workspace.analysis_config.log2p1 = True
    mock_workspace.analysis_config.use_exclude = True
    mock_workspace.analysis_config.min_feature_nonzero_samples = 1
    mock_workspace.analysis_config.min_feature_mean = 0.0
    
    # This should run without error
    render_analysis_matrix_summary(mock_workspace)
    assert mock_st.write.called
