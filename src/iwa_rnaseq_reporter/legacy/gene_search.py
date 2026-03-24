from __future__ import annotations

import pandas as pd
from .analysis import build_analysis_matrix


def search_features(index: pd.Index, query: str, max_hits: int = 50) -> list[str]:
    """
    Search for feature IDs in the index that match the query.
    Case-insensitive substring search.
    """
    if not query:
        return []

    query = query.lower()
    hits = [str(idx) for idx in index if query in str(idx).lower()]
    return hits[:max_hits]


def build_feature_profile_table(
    ds,
    feature_id: str,
    matrix_kind: str = "gene_tpm",
    log2p1: bool = True,
    use_exclude: bool = True,
    min_feature_nonzero_samples: int = 1,
    min_feature_mean: float = 0.0,
) -> pd.DataFrame:
    """
    Extract expression values for a specific feature across selected samples.
    Merged with sample metadata.
    """
    matrix = build_analysis_matrix(
        ds,
        matrix_kind=matrix_kind,
        log2p1=log2p1,
        use_exclude=use_exclude,
        min_feature_nonzero_samples=min_feature_nonzero_samples,
        min_feature_mean=min_feature_mean,
    )

    if feature_id not in matrix.index:
        raise ValueError(f"Feature '{feature_id}' not found in the current analysis matrix.")

    profile = matrix.loc[feature_id].to_frame(name="expression_value")
    profile.index.name = "sample_id"
    profile = profile.reset_index()

    # Merge with metadata
    md = ds.sample_metadata.copy()
    md["sample_id"] = md["sample_id"].astype(str)
    
    # We use inner join to keep only samples used in the analysis matrix
    profile = profile.merge(md, on="sample_id", how="inner")
    
    return profile
