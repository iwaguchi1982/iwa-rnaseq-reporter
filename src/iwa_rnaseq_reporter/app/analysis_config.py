from dataclasses import dataclass
from typing import List

# Standard matrix kinds supported by the application
VALID_MATRIX_KINDS = ["gene_tpm", "gene_numreads", "transcript_tpm", "transcript_numreads"]

@dataclass(frozen=True)
class AnalysisConfig:
    """
    Standard configuration for data analysis.
    This captures filtering and transformation parameters once resolved from UI inputs.
    """
    matrix_kind: str
    log2p1: bool
    use_exclude: bool
    min_feature_nonzero_samples: int
    min_feature_mean: float


def validate_analysis_config(config: AnalysisConfig):
    """
    Validates that the analysis configuration has valid ranges and values.
    """
    if config.matrix_kind not in VALID_MATRIX_KINDS:
        raise ValueError(
            f"Invalid matrix_kind: {config.matrix_kind}. "
            f"Must be one of {VALID_MATRIX_KINDS}"
        )

    if config.min_feature_nonzero_samples < 0:
        raise ValueError(
            f"min_feature_nonzero_samples must be >= 0, got {config.min_feature_nonzero_samples}"
        )
    
    if config.min_feature_mean < 0:
        raise ValueError(f"min_feature_mean must be >= 0, got {config.min_feature_mean}")


def normalize_analysis_config(config: AnalysisConfig) -> AnalysisConfig:
    """
    Normalizes a configuration (e.g., ensuring correct types).
    Currently returns the config as is, as the dataclass already provides basic structuring.
    """
    return config
