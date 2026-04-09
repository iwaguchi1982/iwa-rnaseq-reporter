from typing import Any
from iwa_rnaseq_reporter.legacy.analysis import (
    get_analysis_sample_ids,
    build_analysis_sample_table,
    build_analysis_matrix,
)
from .analysis_config import AnalysisConfig
from .analysis_workspace_context import AnalysisWorkspaceContext

def build_analysis_workspace(dataset: Any, config: AnalysisConfig) -> AnalysisWorkspaceContext:
    """
    Orchestrate the creation of an AnalysisWorkspaceContext from a dataset and config.
    This encapsulates feature filtering, sample selection and transformation logic.
    """
    sample_ids = get_analysis_sample_ids(
        dataset,
        matrix_kind=config.matrix_kind,
        use_exclude=config.use_exclude,
    )

    sample_table = build_analysis_sample_table(
        dataset,
        matrix_kind=config.matrix_kind,
        use_exclude=config.use_exclude,
    )

    matrix = build_analysis_matrix(
        dataset,
        matrix_kind=config.matrix_kind,
        log2p1=config.log2p1,
        use_exclude=config.use_exclude,
        min_feature_nonzero_samples=config.min_feature_nonzero_samples,
        min_feature_mean=config.min_feature_mean,
    )

    return AnalysisWorkspaceContext(
        dataset=dataset,
        analysis_config=config,
        analysis_sample_ids=sample_ids,
        analysis_sample_table=sample_table,
        analysis_matrix=matrix,
    )
