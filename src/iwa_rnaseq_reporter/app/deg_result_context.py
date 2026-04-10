from dataclasses import dataclass
from typing import Optional, Any
import pandas as pd
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig

@dataclass(frozen=True)
class DegThresholdSnapshot:
    """
    Snapshot of thresholds and sort settings used for visualization and export.
    """
    padj_threshold: float
    abs_log2_fc_threshold: float
    sort_by: str
    preview_top_n: int


@dataclass(frozen=True)
class DegSummaryMetrics:
    """
    Aggregated metrics for a DEG result.
    """
    n_features_tested: int
    n_sig_up: int
    n_sig_down: int
    max_abs_log2_fc: float


@dataclass(frozen=True)
class DegResultContext:
    """
    Consolidated context for a DEG result, intended for UI display and export payload.
    Bundles the statistical result with the precise conditions under which it was derived.
    """
    comparison_column: str
    group_a: str
    group_b: str
    matrix_kind: str
    analysis_config_snapshot: AnalysisConfig
    deg_result: Any  # Raw result from compute_statistical_deg
    result_table: pd.DataFrame  # Processed table (annotated, sorted)
    summary_metrics: DegSummaryMetrics
    threshold_snapshot: DegThresholdSnapshot

    @property
    def has_results(self) -> bool:
        return not self.result_table.empty

    @property
    def comparison_label(self) -> str:
        return f"{self.group_a} vs {self.group_b} ({self.comparison_column})"

    @property
    def n_features_tested(self) -> int:
        return self.summary_metrics.n_features_tested
