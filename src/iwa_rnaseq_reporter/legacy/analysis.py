from __future__ import annotations

import numpy as np
import pandas as pd
from iwa_rnaseq_reporter.shared.matrix_kinds import VALID_MATRIX_KINDS




def get_matrix_by_kind(ds, matrix_kind: str) -> pd.DataFrame:
    """
    Return a matrix DataFrame from ReporterDataset by logical matrix name.
    """
    if matrix_kind not in VALID_MATRIX_KINDS:
        raise ValueError(f"Unsupported matrix_kind: {matrix_kind}")

    matrix = getattr(ds, matrix_kind, None)
    if matrix is None:
        raise ValueError(f"Matrix not available for matrix_kind={matrix_kind}")

    return matrix.copy()


def get_analysis_sample_ids(
    ds,
    matrix_kind: str = "gene_tpm",
    use_exclude: bool = True,
) -> list[str]:
    """
    Determine analysis sample IDs using sample_metadata and the specified matrix columns.

    Rules:
    - matrix column order is preserved
    - only samples present in matrix are returned
    - if use_exclude=True, rows with exclude=True are removed
    """
    md = ds.sample_metadata.copy()
    if "sample_id" not in md.columns:
        raise ValueError("sample_metadata must contain sample_id")

    md["sample_id"] = md["sample_id"].astype(str)

    if "exclude" in md.columns and use_exclude:
        include_ids = md.loc[~md["exclude"], "sample_id"].tolist()
    else:
        include_ids = md["sample_id"].tolist()

    # Get matrix to find master column list
    matrix = get_matrix_by_kind(ds, matrix_kind)
    matrix_ids = list(map(str, matrix.columns))
    return [s for s in matrix_ids if s in include_ids]


def filter_features(
    matrix: pd.DataFrame,
    min_feature_nonzero_samples: int = 1,
    min_feature_mean: float = 0.0,
) -> pd.DataFrame:
    """
    Filter features (rows) of the matrix by nonzero sample count and mean value.
    """
    out = matrix.copy()

    if min_feature_nonzero_samples > 1:
        nonzero_counts = (out.fillna(0) > 0).sum(axis=1)
        out = out.loc[nonzero_counts >= min_feature_nonzero_samples].copy()

    if min_feature_mean > 0:
        means = out.mean(axis=1, skipna=True)
        out = out.loc[means >= min_feature_mean].copy()

    return out


def build_analysis_matrix(
    ds,
    matrix_kind: str = "gene_tpm",
    log2p1: bool = True,
    use_exclude: bool = True,
    min_feature_nonzero_samples: int = 1,
    min_feature_mean: float = 0.0,
) -> pd.DataFrame:
    """
    Build an analysis-ready matrix with selected samples and optional transform.

    Output:
    - rows: features
    - columns: selected sample_ids
    """
    matrix = get_matrix_by_kind(ds, matrix_kind)
    sample_ids = get_analysis_sample_ids(ds, matrix_kind=matrix_kind, use_exclude=use_exclude)

    if not sample_ids:
        raise ValueError("No analysis samples selected")

    # Select samples
    matrix = matrix.loc[:, sample_ids].copy()

    # Filter features
    matrix = filter_features(
        matrix,
        min_feature_nonzero_samples=min_feature_nonzero_samples,
        min_feature_mean=min_feature_mean,
    )

    if matrix.empty:
        raise ValueError("No features remain after filtering")

    if log2p1:
        matrix = np.log2(matrix.astype(float) + 1.0)

    return matrix


def build_analysis_sample_table(
    ds,
    matrix_kind: str = "gene_tpm",
    use_exclude: bool = True,
) -> pd.DataFrame:
    """
    Return sample metadata table with an 'analysis_included' column.
    Useful for UI preview.
    """
    md = ds.sample_metadata.copy()
    md["sample_id"] = md["sample_id"].astype(str)

    selected = set(get_analysis_sample_ids(ds, matrix_kind=matrix_kind, use_exclude=use_exclude))
    md["analysis_included"] = md["sample_id"].isin(selected)

    preferred = [
        "sample_id",
        "display_name",
        "group",
        "condition",
        "replicate",
        "batch",
        "exclude",
        "analysis_included",
    ]
    ordered = [c for c in preferred if c in md.columns]
    remaining = [c for c in md.columns if c not in ordered]

    return md[ordered + remaining]


def add_display_labels(
    df: pd.DataFrame, 
    feature_annotation: pd.DataFrame | None,
    id_column: str = "feature_id"
) -> pd.DataFrame:
    """
    Merge gene symbols from feature_annotation into the target DataFrame.
    Adds 'gene_symbol' and 'display_label' columns.
    If annotation is missing or symbol is empty, 'display_label' falls back to the ID.
    """
    out = df.copy()
    
    # 1. Identify the feature identifier column
    # Fallback candidates if the explicit id_column is not found
    id_candidates = [id_column, "feature_id", "gene_id", "transcript_id"]
    
    found_id_col = None
    for cand in id_candidates:
        if cand in out.columns:
            found_id_col = cand
            break
            
    if found_id_col is None:
        # Check index
        idx_name = str(out.index.name) if out.index.name else "None"
        if any(cand.lower() in idx_name.lower() for cand in id_candidates) or not out.index.name:
            out = out.reset_index()
            # The newly reset index is the first column
            # Use original index name if it exists, else use id_column
            old_idx_col = out.columns[0]
            out = out.rename(columns={old_idx_col: id_column})
            found_id_col = id_column
        else:
            # Cannot identify ID column
            return out

    # Standardize our internal ID column name if necessary
    if found_id_col != id_column:
        out = out.rename(columns={found_id_col: id_column})
        found_id_col = id_column

    if feature_annotation is None or "feature_id" not in feature_annotation.columns:
        # Fallback: display_label = feature_id
        out["gene_symbol"] = ""
        out["display_label"] = out[id_column].astype(str)
        return out

    # 2. Merge annotation
    if "gene_symbol" not in feature_annotation.columns:
        # Annotation file exists but lacks the required gene_symbol column
        out["gene_symbol"] = ""
        out["display_label"] = out[id_column].astype(str)
        return out

    # Ensure feature_id is string for stable join
    fa = feature_annotation[["feature_id", "gene_symbol"]].copy()
    fa["feature_id"] = fa["feature_id"].astype(str)
    out[id_column] = out[id_column].astype(str)
    
    out = out.merge(fa, left_on=id_column, right_on="feature_id", how="left", suffixes=("", "_ann"))
    
    # Clean up duplicate feature_id if necessary
    if "feature_id_ann" in out.columns:
        out = out.drop(columns=["feature_id_ann"])

    # 3. Create display_label
    # Use gene_symbol if available and not NaN/empty, else fallback to feature_id
    out["gene_symbol"] = out["gene_symbol"].fillna("")
    out["display_label"] = out["gene_symbol"].where(out["gene_symbol"] != "", out[id_column])
    
    return out
