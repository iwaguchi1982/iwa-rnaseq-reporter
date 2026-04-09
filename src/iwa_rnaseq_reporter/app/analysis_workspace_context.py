from dataclasses import dataclass
from typing import Any, List
import pandas as pd
from .analysis_config import AnalysisConfig

@dataclass(frozen=True)
class AnalysisWorkspaceContext:
    """
    Consolidates the analysis workspace state.
    Bundles the configuration and the derived data for downstream consumption.
    """
    dataset: Any
    analysis_config: AnalysisConfig
    analysis_sample_ids: List[str]
    analysis_sample_table: pd.DataFrame
    analysis_matrix: pd.DataFrame

    @property
    def sample_count(self) -> int:
        return len(self.analysis_sample_ids)

    @property
    def feature_count(self) -> int:
        return len(self.analysis_matrix.index)

    @property
    def has_samples(self) -> bool:
        return self.sample_count > 0

    @property
    def has_features(self) -> bool:
        return self.feature_count > 0

    @property
    def matrix_kind(self) -> str:
        return self.analysis_config.matrix_kind
