import pytest
from iwa_rnaseq_reporter.app.analysis_config import (
    AnalysisConfig, 
    validate_analysis_config
)
from iwa_rnaseq_reporter.shared.matrix_kinds import VALID_MATRIX_KINDS

def test_analysis_config_creation():
    """
    Verify that AnalysisConfig can be created with valid parameters 
    and holds them correctly.
    """
    config = AnalysisConfig(
        matrix_kind="gene_tpm",
        log2p1=True,
        use_exclude=True,
        min_feature_nonzero_samples=2,
        min_feature_mean=0.5
    )
    assert config.matrix_kind == "gene_tpm"
    assert config.log2p1 is True
    assert config.use_exclude is True
    assert config.min_feature_nonzero_samples == 2
    assert config.min_feature_mean == 0.5


def test_validate_analysis_config_success():
    """
    Verify that valid configurations pass the validation check.
    """
    for kind in VALID_MATRIX_KINDS:
        config = AnalysisConfig(kind, True, True, 0, 0.0)
        validate_analysis_config(config)


def test_validate_analysis_config_failure_invalid_kind():
    """
    Verify that unsupported matrix_kind raises ValueError.
    """
    config = AnalysisConfig("invalid_kind", True, True, 1, 0.0)
    with pytest.raises(ValueError, match="Invalid matrix_kind"):
        validate_analysis_config(config)


def test_validate_analysis_config_failure_nonzero_samples():
    """
    Verify that negative min_feature_nonzero_samples raises ValueError.
    """
    config = AnalysisConfig("gene_tpm", True, True, -1, 0.0)
    with pytest.raises(ValueError, match="min_feature_nonzero_samples"):
        validate_analysis_config(config)


def test_validate_analysis_config_failure_min_mean():
    """
    Verify that negative min_feature_mean raises ValueError.
    """
    config = AnalysisConfig("gene_tpm", True, True, 2, -0.1)
    with pytest.raises(ValueError, match="min_feature_mean"):
        validate_analysis_config(config)


def test_analysis_config_is_pure_dataclass():
    """
    Verify that the config does not have external dependencies or complex state.
    """
    config = AnalysisConfig("gene_tpm", False, False, 1, 1.0)
    # Check that it is indeed a dataclass and has expected fields
    from dataclasses import is_dataclass
    assert is_dataclass(config)
