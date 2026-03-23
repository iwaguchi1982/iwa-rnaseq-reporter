from __future__ import annotations

import pandas as pd


def compute_feature_statistics(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute basic statistics for each feature (row) in the matrix.
    """
    if matrix_df.empty:
        return pd.DataFrame()

    stats = pd.DataFrame(index=matrix_df.index)
    stats["mean"] = matrix_df.mean(axis=1)
    stats["variance"] = matrix_df.var(axis=1)
    stats["nonzero_samples"] = (matrix_df > 0).sum(axis=1)
    stats["max_value"] = matrix_df.max(axis=1)
    stats["min_value"] = matrix_df.min(axis=1)
    
    return stats


def get_top_variable_features(
    matrix_df: pd.DataFrame,
    top_n: int = 50,
) -> pd.DataFrame:
    """
    Calculate feature statistics and return the top N features sorted by variance.
    """
    stats = compute_feature_statistics(matrix_df)
    if stats.empty:
        return stats

    top_features = stats.sort_values("variance", ascending=False).head(top_n)
    return top_features
