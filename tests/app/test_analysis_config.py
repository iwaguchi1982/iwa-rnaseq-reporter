import pytest
from iwa_rnaseq_reporter.app.analysis_config import (
    AnalysisConfig, 
    validate_analysis_config, 
    normalize_analysis_config
)

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
    config = AnalysisConfig("gene_tpm", True, True, 0, 0.0)
    validate_analysis_config(config)  # Should not raise


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


def test_normalize_analysis_config():
    """
    Verify that normalization returns the config (basic contract check).
    """
    config = AnalysisConfig("gene_tpm", True, True, 2, 0.5)
    normalized = normalize_analysis_config(config)
    assert normalized == config


def test_analysis_config_is_pure_dataclass():
    """
    Verify that the config does not have external dependencies or complex state.
    """
    config = AnalysisConfig("kind", False, False, 1, 1.0)
    # Check that it is indeed a dataclass and has expected fields
    from dataclasses import is_dataclass
    assert is_dataclass(config)
