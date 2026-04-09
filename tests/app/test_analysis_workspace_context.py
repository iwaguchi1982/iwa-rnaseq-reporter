import pytest
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig

def test_analysis_workspace_context_creation():
    """
    Verify that AnalysisWorkspaceContext can be created and holds expected data.
    """
    mock_ds = MagicMock()
    config = AnalysisConfig(
        matrix_kind="gene_tpm",
        log2p1=True,
        use_exclude=True,
        min_feature_nonzero_samples=2,
        min_feature_mean=0.5
    )
    sample_ids = ["s1", "s2"]
    sample_table = pd.DataFrame({"sample_id": ["s1", "s2"]})
    matrix = pd.DataFrame(
        [[1.0, 2.0], [3.0, 4.0]], 
        index=["f1", "f2"], 
        columns=["s1", "s2"]
    )
    
    workspace = AnalysisWorkspaceContext(
        dataset=mock_ds,
        analysis_config=config,
        analysis_sample_ids=sample_ids,
        analysis_sample_table=sample_table,
        analysis_matrix=matrix
    )
    
    assert workspace.dataset == mock_ds
    assert workspace.analysis_config == config
    assert workspace.analysis_sample_ids == sample_ids
    assert workspace.sample_count == 2
    assert workspace.feature_count == 2
    assert workspace.has_samples is True
    assert workspace.has_features is True
    assert workspace.matrix_kind == "gene_tpm"

def test_analysis_workspace_context_empty():
    """
    Verify property behavior with empty data.
    """
    matrix = pd.DataFrame()
    workspace = AnalysisWorkspaceContext(
        dataset=None,
        analysis_config=AnalysisConfig("gene_tpm", True, True, 1, 0.0),
        analysis_sample_ids=[],
        analysis_sample_table=pd.DataFrame(),
        analysis_matrix=matrix
    )
    
    assert workspace.sample_count == 0
    assert workspace.feature_count == 0
    assert workspace.has_samples is False
    assert workspace.has_features is False
