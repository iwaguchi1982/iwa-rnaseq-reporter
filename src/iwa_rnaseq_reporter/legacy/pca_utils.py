from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def select_top_variable_features(
    matrix_df: pd.DataFrame,
    top_n: int | None = 500,
) -> pd.DataFrame:
    """
    Select top variable features by variance across samples.

    Input:
    - rows: features
    - columns: samples
    """
    if matrix_df.empty:
        raise ValueError("Input matrix is empty")

    if top_n is None:
        return matrix_df.copy()

    if top_n <= 0:
        raise ValueError("top_n must be > 0 or None")

    variances = matrix_df.var(axis=1, skipna=True)
    top_features = variances.sort_values(ascending=False).head(top_n).index
    return matrix_df.loc[top_features].copy()


def run_pca(
    matrix_df: pd.DataFrame,
    n_components: int = 5,
    scale: bool = False,
) -> tuple[pd.DataFrame, list[float]]:
    """
    Run PCA on a feature x sample matrix.

    Input:
    - rows: features
    - columns: samples

    Output:
    - pca_scores_df: rows=samples, columns=PC1..PCk
    - explained_variance_ratio: list[float]
    """
    if matrix_df.empty:
        raise ValueError("PCA input matrix is empty")

    n_features, n_samples = matrix_df.shape
    if n_samples < 2:
        raise ValueError("PCA requires at least 2 samples.")

    X = matrix_df.T.astype(float).values  # samples x features

    if np.isnan(X).any():
        raise ValueError("PCA input contains NaN values.")

    if scale:
        X = StandardScaler().fit_transform(X)

    max_components = min(n_components, X.shape[0], X.shape[1])
    if max_components < 1:
        raise ValueError("Could not determine valid PCA component count.")

    pca = PCA(n_components=max_components)
    scores = pca.fit_transform(X)

    columns = [f"PC{i+1}" for i in range(scores.shape[1])]
    pca_scores_df = pd.DataFrame(scores, index=matrix_df.columns, columns=columns)

    explained = pca.explained_variance_ratio_.tolist()
    return pca_scores_df, explained


def build_pca_plot_df(
    ds,
    matrix_df: pd.DataFrame,
    explained_variance_ratio: list[float],
    use_exclude: bool = True,
) -> pd.DataFrame:
    """
    Merge PCA scores with sample metadata for plotting.

    Input matrix_df should be the PCA score table:
    - rows: samples
    - columns: PC1, PC2, ...

    Returns a plotting table with metadata columns merged by sample_id.
    """
    plot_df = matrix_df.copy().reset_index().rename(columns={"index": "sample_id"})
    plot_df["sample_id"] = plot_df["sample_id"].astype(str)

    md = ds.sample_metadata.copy()
    md["sample_id"] = md["sample_id"].astype(str)

    if "exclude" in md.columns and use_exclude:
        md = md.loc[~md["exclude"]].copy()

    plot_df = plot_df.merge(md, on="sample_id", how="inner")

    if "display_name" not in plot_df.columns:
        plot_df["display_name"] = plot_df["sample_id"]
    else:
        plot_df["display_name"] = plot_df["display_name"].fillna(plot_df["sample_id"])

    if len(explained_variance_ratio) >= 1:
        plot_df.attrs["pc1_label"] = f"PC1 ({explained_variance_ratio[0] * 100:.1f}%)"
    else:
        plot_df.attrs["pc1_label"] = "PC1"

    if len(explained_variance_ratio) >= 2:
        plot_df.attrs["pc2_label"] = f"PC2 ({explained_variance_ratio[1] * 100:.1f}%)"
    else:
        plot_df.attrs["pc2_label"] = "PC2"

    return plot_df
