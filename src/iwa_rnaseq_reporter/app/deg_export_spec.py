from dataclasses import dataclass, asdict
from typing import Any, Dict
import pandas as pd
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

@dataclass(frozen=True)
class DegExportSummarySpec:
    """
    Core metadata identifying the comparison logic and group sizes.
    """
    comparison_column: str
    group_a: str
    group_b: str
    comparison_label: str
    sample_count_group_a: int
    sample_count_group_b: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DegExportRunMetadataSpec:
    """
    Capture technical parameters and thresholds used for the DEG run.
    """
    matrix_kind: str
    log2p1: bool
    use_exclude: bool
    min_feature_nonzero_samples: int
    min_feature_mean: float
    padj_threshold: float
    abs_log2_fc_threshold: float
    sort_by: str
    preview_top_n: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DegExportPayload:
    """
    Consolidated payload ready for external serialization (CSV, JSON, Zenodo, etc.).
    Keeps a pointer to the result table (DataFrame).
    """
    summary: DegExportSummarySpec
    metadata: DegExportRunMetadataSpec
    result_table: pd.DataFrame
    summary_metrics: DegSummaryMetrics

    @property
    def has_results(self) -> bool:
        return not self.result_table.empty
