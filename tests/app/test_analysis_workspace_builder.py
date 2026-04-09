import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.analysis_workspace_builder import build_analysis_workspace
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext

def test_build_analysis_workspace_success():
    """
    Verify that build_analysis_workspace correctly orchestrates 
    the creation of a workspace.
    """
    # Mock dataset
    mock_ds = MagicMock()
    # Mocking matrices for legacy helper calls
    mock_matrix = pd.DataFrame(
        [[10.0, 20.0]], 
        index=["gene1"], 
        columns=["S1", "S2"]
    )
    mock_ds.gene_tpm = mock_matrix
    mock_ds.sample_metadata = pd.DataFrame({
        "sample_id": ["S1", "S2"],
        "exclude": [False, False]
    })
    mock_ds.feature_annotation = None

    config = AnalysisConfig(
        matrix_kind="gene_tpm",
        log2p1=False,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0
    )

    workspace = build_analysis_workspace(mock_ds, config)

    assert isinstance(workspace, AnalysisWorkspaceContext)
    assert workspace.matrix_kind == "gene_tpm"
    assert workspace.sample_count == 2
    assert workspace.feature_count == 1
    # Check that analysis_matrix is indeed what we expect (subset/transform of mock)
    pd.testing.assert_frame_equal(workspace.analysis_matrix, mock_matrix)

def test_build_analysis_workspace_failure_propagation():
    """
    Verify that failures from legacy helpers are propagated.
    """
    mock_ds = MagicMock()
    mock_ds.gene_tpm = pd.DataFrame() # Empty matrix
    mock_ds.sample_metadata = pd.DataFrame({"sample_id": []})

    config = AnalysisConfig(
        matrix_kind="gene_tpm",
        log2p1=True,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0
    )

    # get_analysis_sample_ids or build_analysis_matrix should fail/raise if nothing remains
    # In legacy analysis.py, build_analysis_matrix raises ValueError if matrix is empty
    with pytest.raises(ValueError):
        build_analysis_workspace(mock_ds, config)
