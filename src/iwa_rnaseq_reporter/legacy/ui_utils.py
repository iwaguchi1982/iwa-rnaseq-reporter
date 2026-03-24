from __future__ import annotations

import pandas as pd


def format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Polishes DataFrame for display by filling NAs and standardizing formats.
    """
    return df.fillna("-").replace("", "-")


def get_nonempty_metadata_columns(
    df: pd.DataFrame,
    candidate_columns: list[str],
) -> list[str]:
    """
    Filter candidate columns to those that actually exist and contain non-empty data.
    """
    cols = []
    for c in candidate_columns:
        if c not in df.columns:
            continue
        # We strip and check for non-empty string. NaNs are handled by fillna.
        values = df[c].fillna("").astype(str).str.strip()
        if (values != "").any() and (values != "-").any() and (values != "Unknown").any():
            cols.append(c)
    return cols
