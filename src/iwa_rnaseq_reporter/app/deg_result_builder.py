import pandas as pd
from typing import Any
from iwa_rnaseq_reporter.legacy.analysis import add_display_labels
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext
from .deg_result_context import (
    DegResultContext,
    DegThresholdSnapshot,
    DegSummaryMetrics
)

def build_deg_result_context(
    workspace: AnalysisWorkspaceContext,
    deg_input_obj: Any,
    comparison_column: str,
    group_a: str,
    group_b: str,
    deg_res: Any,
    p_thresh: float,
    fc_thresh: float,
    sort_by: str,
    top_n: int
) -> DegResultContext:
    """
    Build a DegResultContext from statistical results and UI settings.
    Orchestrates table labeling, sorting, and metrics calculation.
    """
    # 1. Take a snapshot of thresholds
    threshold_snapshot = DegThresholdSnapshot(
        padj_threshold=p_thresh,
        abs_log2_fc_threshold=fc_thresh,
        sort_by=sort_by,
        preview_top_n=top_n
    )

    # 2. Process Result Table (Annotate, Sort, Reorder)
    res_df = deg_res.result_table.copy()
    
    # Standard labeling
    res_df = add_display_labels(res_df, workspace.dataset.feature_annotation)

    # Sorting
    if sort_by in res_df.columns:
        ascending = True if sort_by in ["padj", "p_value"] else False
        res_df = res_df.sort_values(by=sort_by, ascending=ascending)

    # Standard column ordering
    preferred_cols = [
        "rank_by_padj", "display_label", "gene_symbol", "feature_id", "log2_fc", 
        "padj", "p_value", "direction", "mean_group_a", "mean_group_b", "abs_log2_fc"
    ]
    display_cols = [c for c in preferred_cols if c in res_df.columns]
    other_cols = [c for c in res_df.columns if c not in display_cols]
    res_df = res_df[display_cols + other_cols]

    # 3. Calculate Summary Metrics
    sig_up = res_df[(res_df["padj"] < p_thresh) & (res_df["log2_fc"] > fc_thresh)]
    sig_dn = res_df[(res_df["padj"] < p_thresh) & (res_df["log2_fc"] < -fc_thresh)]
    max_abs_fc = res_df["abs_log2_fc"].max() if not res_df.empty else 0.0

    summary_metrics = DegSummaryMetrics(
        n_features_tested=int(deg_res.n_features_tested),
        n_sig_up=len(sig_up),
        n_sig_down=len(sig_dn),
        max_abs_log2_fc=float(max_abs_fc)
    )

    # 4. Assemble Context
    return DegResultContext(
        comparison_column=comparison_column,
        group_a=group_a,
        group_b=group_b,
        matrix_kind=workspace.matrix_kind,
        analysis_config_snapshot=workspace.analysis_config,
        deg_result=deg_res,
        result_table=res_df,
        summary_metrics=summary_metrics,
        threshold_snapshot=threshold_snapshot
    )
