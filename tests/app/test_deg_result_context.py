import pytest
import pandas as pd
from iwa_rnaseq_reporter.app.deg_result_context import (
    DegResultContext,
    DegThresholdSnapshot,
    DegSummaryMetrics
)
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig

def test_deg_result_context_properties():
    """
    Verify basic properties of DegResultContext.
    """
    config = AnalysisConfig("gene_tpm", True, True, 1, 0.0)
    thresh = DegThresholdSnapshot(0.05, 1.0, "padj", 100)
    metrics = DegSummaryMetrics(100, 10, 5, 5.0)
    
    context = DegResultContext(
        comparison_column="group",
        group_a="A",
        group_b="B",
        matrix_kind="gene_tpm",
        analysis_config_snapshot=config,
        deg_result=None,
        result_table=pd.DataFrame({"gene": ["G1"]}),
        summary_metrics=metrics,
        threshold_snapshot=thresh
    )
    
    assert context.has_results is True
    assert context.comparison_label == "A vs B (group)"
    assert context.n_features_tested == 100
    assert context.matrix_kind == "gene_tpm"

def test_deg_result_context_empty():
    """
    Verify behavior with empty result table.
    """
    metrics = DegSummaryMetrics(0, 0, 0, 0.0)
    context = DegResultContext(
        comparison_column="group",
        group_a="A",
        group_b="B",
        matrix_kind="gene_tpm",
        analysis_config_snapshot=None,
        deg_result=None,
        result_table=pd.DataFrame(),
        summary_metrics=metrics,
        threshold_snapshot=None
    )
    assert context.has_results is False
