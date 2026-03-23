from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.pca_utils import (
    build_pca_plot_df,
    run_pca,
    select_top_variable_features,
)


def test_select_top_variable_features_basic():
    df = pd.DataFrame(
        {
            "S1": [1.0, 1.0, 10.0],
            "S2": [1.0, 2.0, 20.0],
            "S3": [1.0, 3.0, 30.0],
        },
        index=["gene_flat", "gene_mid", "gene_high"],
    )

    out = select_top_variable_features(df, top_n=2)

    assert out.shape == (2, 3)
    assert "gene_flat" not in out.index


def test_select_top_variable_features_none_returns_copy():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0],
            "S2": [3.0, 4.0],
        },
        index=["g1", "g2"],
    )

    out = select_top_variable_features(df, top_n=None)

    assert out.shape == df.shape
    assert list(out.index) == ["g1", "g2"]


def test_run_pca_basic():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0, 3.0],
            "S2": [2.0, 3.0, 4.0],
            "S3": [10.0, 11.0, 12.0],
        },
        index=["g1", "g2", "g3"],
    )

    scores_df, explained = run_pca(df, n_components=3, scale=False)

    assert list(scores_df.index) == ["S1", "S2", "S3"]
    assert "PC1" in scores_df.columns
    assert len(explained) >= 1


def test_run_pca_with_scaling():
    df = pd.DataFrame(
        {
            "S1": [1.0, 100.0, 3.0],
            "S2": [2.0, 110.0, 4.0],
            "S3": [10.0, 900.0, 12.0],
        },
        index=["g1", "g2", "g3"],
    )

    scores_df, explained = run_pca(df, n_components=2, scale=True)

    assert scores_df.shape[0] == 3
    assert scores_df.shape[1] == 2
    assert len(explained) == 2


def test_run_pca_requires_at_least_two_samples():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0, 3.0],
        },
        index=["g1", "g2", "g3"],
    )

    with pytest.raises(ValueError, match="at least 2 samples"):
        run_pca(df)


def test_run_pca_rejects_nan():
    df = pd.DataFrame(
        {
            "S1": [1.0, np.nan, 3.0],
            "S2": [2.0, 3.0, 4.0],
        },
        index=["g1", "g2", "g3"],
    )

    with pytest.raises(ValueError, match="NaN"):
        run_pca(df)


def test_build_pca_plot_df_merges_metadata(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    scores_df = pd.DataFrame(
        {
            "PC1": [0.1, -0.1],
            "PC2": [0.2, -0.2],
        },
        index=["SRR518891", "SRR518892"],
    )

    plot_df = build_pca_plot_df(ds, scores_df, [0.7, 0.2], use_exclude=True)

    assert "sample_id" in plot_df.columns
    assert "display_name" in plot_df.columns
    assert plot_df.attrs["pc1_label"].startswith("PC1")
    assert plot_df.attrs["pc2_label"].startswith("PC2")


def test_build_pca_plot_df_respects_exclude(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df.loc[df["sample_id"] == "SRR518892", "exclude"] = True
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    scores_df = pd.DataFrame(
        {
            "PC1": [0.1, -0.1],
            "PC2": [0.2, -0.2],
        },
        index=["SRR518891", "SRR518892"],
    )

    plot_df = build_pca_plot_df(ds, scores_df, [0.7, 0.2], use_exclude=True)

    assert plot_df["sample_id"].tolist() == ["SRR518891"]
