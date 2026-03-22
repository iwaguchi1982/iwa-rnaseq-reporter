from __future__ import annotations

import pandas as pd


def normalize_sample_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize sample metadata: fill defaults and standardize types."""
    df = df.copy()

    # display_name 補完
    if "display_name" in df.columns:
        df["display_name"] = df["display_name"].fillna("").astype(str)
        mask = df["display_name"].str.strip() == ""
        if "sample_id" in df.columns:
            df.loc[mask, "display_name"] = df.loc[mask, "sample_id"]
    elif "sample_id" in df.columns:
        df["display_name"] = df["sample_id"]

    # condition 補完 (condition が空なら group)
    if "condition" in df.columns and "group" in df.columns:
        df["condition"] = df["condition"].fillna("").astype(str)
        mask = df["condition"].str.strip() == ""
        df.loc[mask, "condition"] = df.loc[mask, "group"]
    elif "group" in df.columns and "condition" not in df.columns:
        df["condition"] = df["group"]

    # exclude bool 正規化
    if "exclude" in df.columns:
        # Convert Various formats to bool
        def to_bool(val):
            if isinstance(val, bool):
                return val
            s = str(val).lower().strip()
            return s in ("true", "1", "yes", "t", "y")

        df["exclude"] = df["exclude"].apply(to_bool)
    else:
        df["exclude"] = False

    return df


def normalize_sample_qc_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize sample QC summary."""
    df = df.copy()
    # Ensure sample_id is present and string
    if "sample_id" in df.columns:
        df["sample_id"] = df["sample_id"].astype(str)
    return df


def normalize_expression_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure expression matrix is numeric and columns are strings."""
    df = df.copy()
    df.columns = df.columns.astype(str)
    df = df.apply(pd.to_numeric, errors="coerce")
    return df
