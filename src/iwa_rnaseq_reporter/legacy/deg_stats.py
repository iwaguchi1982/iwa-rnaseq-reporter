from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from .deg_input import DEGInput, DEGResult


def compute_statistical_deg(
    deg_input: DEGInput,
    method: str = "welch_ttest",
    padj_method: str = "fdr_bh",
) -> DEGResult:
    """
    Perform statistical differential expression testing.
    Currently supports Welch's t-test (default).
    """
    mat = deg_input.feature_matrix.copy()
    if mat.empty:
        return DEGResult(
            comparison_column=deg_input.group_column,
            group_a=deg_input.group_a,
            group_b=deg_input.group_b,
            result_table=pd.DataFrame(),
            n_features_tested=0,
            method=method,
            padj_method=padj_method,
            matrix_kind=deg_input.matrix_kind,
            log2p1=False, # Placeholder
        )

    a_cols = deg_input.group_a_samples
    b_cols = deg_input.group_b_samples
    
    a_data = mat.loc[:, a_cols].values
    b_data = mat.loc[:, b_cols].values

    # 1. Compute p-values per feature
    # Using scipy.stats.ttest_ind with equal_var=False for Welch's t-test
    t_stats, p_values = stats.ttest_ind(b_data, a_data, axis=1, equal_var=False)
    
    # 2. Compute means and log2 fold change (same as preview logic)
    mean_a = np.mean(a_data, axis=1)
    mean_b = np.mean(b_data, axis=1)
    # Using stable pseudocount log-ratio
    log2_fc = np.log2(mean_b + 1.0) - np.log2(mean_a + 1.0)

    # 3. Apply multiple testing correction
    # Filter out NaNs for multipletests
    valid_mask = ~np.isnan(p_values)
    padj = np.full(p_values.shape, np.nan)
    
    if np.any(valid_mask):
        _, corrected_p, _, _ = multipletests(
            p_values[valid_mask], 
            alpha=0.05, 
            method=padj_method
        )
        padj[valid_mask] = corrected_p

    # 4. Build result table
    result_table = pd.DataFrame(
        {
            "feature_id": mat.index.astype(str),
            "mean_group_a": mean_a,
            "mean_group_b": mean_b,
            "log2_fc": log2_fc,
            "abs_log2_fc": np.abs(log2_fc),
            "direction": ["Up" if fc > 0 else "Down" if fc < 0 else "-" for fc in log2_fc],
            "statistic": t_stats,
            "p_value": p_values,
            "padj": padj,
        }
    )

    # Add ranks
    result_table = result_table.sort_values("padj", ascending=True).reset_index(drop=True)
    result_table.insert(0, "rank_by_padj", result_table.index + 1)

    return DEGResult(
        comparison_column=deg_input.group_column,
        group_a=deg_input.group_a,
        group_b=deg_input.group_b,
        result_table=result_table,
        n_features_tested=int(np.sum(valid_mask)),
        method=method,
        padj_method=padj_method,
        matrix_kind=deg_input.matrix_kind,
        log2p1=True, # Assuming log2p1 for now, should ideally be passed in
    )
