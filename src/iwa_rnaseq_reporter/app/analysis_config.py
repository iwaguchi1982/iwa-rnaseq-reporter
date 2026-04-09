from dataclasses import dataclass

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
    Validates that the analysis configuration has valid ranges.
    """
    if config.min_feature_nonzero_samples < 0:
        raise ValueError(f"min_feature_nonzero_samples must be >= 0, got {config.min_feature_nonzero_samples}")
    
    if config.min_feature_mean < 0:
        raise ValueError(f"min_feature_mean must be >= 0, got {config.min_feature_mean}")


def normalize_analysis_config(config: AnalysisConfig) -> AnalysisConfig:
    """
    Normalizes a configuration (e.g., ensuring correct types).
    Currently returns the config as is, as the dataclass already provides basic structuring.
    """
    # Type normalization is naturally handled if we create new instance via helper, 
    # but here we just return it to fulfill the contract.
    return config
