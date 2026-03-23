from __future__ import annotations

import pandas as pd


def compute_sample_correlation(
    matrix_df: pd.DataFrame,
    method: str = "pearson",
) -> pd.DataFrame:
    """
    Compute sample-to-sample correlation matrix.

    Input:
    - rows: features
    - columns: samples

    Output:
    - sample x sample correlation matrix
    """
    if matrix_df.empty:
        raise ValueError("Correlation input matrix is empty")

    if matrix_df.shape[1] < 2:
        raise ValueError("Correlation requires at least 2 samples.")

    return matrix_df.corr(method=method)


def build_sample_annotation_table(ds, sample_ids: list[str]) -> pd.DataFrame:
    """
    Build a focused metadata table for the specified samples.
    """
    md = ds.sample_metadata.copy()
    md["sample_id"] = md["sample_id"].astype(str)

    ann = md.loc[md["sample_id"].isin(sample_ids)].copy()

    preferred = [
        "sample_id",
        "display_name",
        "group",
        "condition",
        "replicate",
        "batch",
        "exclude",
    ]
    ordered = [c for c in preferred if c in ann.columns]
    remaining = [c for c in ann.columns if c not in ordered]

    ann = ann[ordered + remaining]
    # Reindex to ensure order matches sample_ids
    ann = ann.set_index("sample_id").reindex(sample_ids).reset_index()

    return ann
