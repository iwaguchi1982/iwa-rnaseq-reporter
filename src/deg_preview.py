from __future__ import annotations

import numpy as np
import pandas as pd

from .deg_input import DEGInput


def build_deg_preview_table(
    deg_input: DEGInput,
    sort_by: str = "abs_log2_fc",
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Build a pre-DEG comparison table without statistical testing.

    Output columns:
    - feature_id
    - mean_group_a
    - mean_group_b
    - log2_fc
    - abs_log2_fc
    - nonzero_group_a
    - nonzero_group_b
    """
    mat = deg_input.feature_matrix.copy()

    if mat.empty:
        raise ValueError("DEG preview input matrix is empty.")

    a_cols = deg_input.group_a_samples
    b_cols = deg_input.group_b_samples

    if not a_cols or not b_cols:
        raise ValueError("Both groups must contain at least one sample.")

    a = mat.loc[:, a_cols]
    b = mat.loc[:, b_cols]

    mean_a = a.mean(axis=1, skipna=True)
    mean_b = b.mean(axis=1, skipna=True)

    # Pseudocount for preview stability
    # Note: If input was already log2(x+1), this calculation is slightly different from raw log-ratio
    # But for a "preview", this is a common stable approximation.
    log2_fc = np.log2(mean_b + 1.0) - np.log2(mean_a + 1.0)

    nonzero_a = (a.fillna(0) > 0).sum(axis=1)
    nonzero_b = (b.fillna(0) > 0).sum(axis=1)

    out = pd.DataFrame(
        {
            "feature_id": mat.index.astype(str),
            "mean_group_a": mean_a.values,
            "mean_group_b": mean_b.values,
            "log2_fc": log2_fc.values,
            "abs_log2_fc": np.abs(log2_fc.values),
            "nonzero_group_a": nonzero_a.values,
            "nonzero_group_b": nonzero_b.values,
        }
    )

    if sort_by not in out.columns:
        raise ValueError(f"sort_by not found: {sort_by}")

    out = out.sort_values(sort_by, ascending=ascending).reset_index(drop=True)
    return out


def summarize_deg_preview(deg_preview_df: pd.DataFrame) -> dict:
    """
    Small summary for UI cards.
    """
    if deg_preview_df.empty:
        return {
            "n_features": 0,
            "n_positive_fc": 0,
            "n_negative_fc": 0,
            "max_abs_log2_fc": None,
        }

    return {
        "n_features": int(len(deg_preview_df)),
        "n_positive_fc": int((deg_preview_df["log2_fc"] > 0).sum()),
        "n_negative_fc": int((deg_preview_df["log2_fc"] < 0).sum()),
        "max_abs_log2_fc": float(deg_preview_df["abs_log2_fc"].max()),
    }
