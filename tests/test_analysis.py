from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import (
    filter_features,
    build_analysis_matrix,
    get_analysis_sample_ids,
    build_analysis_sample_table,
    get_matrix_by_kind,
)


def test_get_matrix_by_kind_gene_tpm(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    mat = get_matrix_by_kind(ds, "gene_tpm")

    assert isinstance(mat, pd.DataFrame)
    assert list(mat.columns) == ["SRR518891", "SRR518892"]


def test_get_analysis_sample_ids_uses_selected_matrix_kind(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    ids_gene = get_analysis_sample_ids(ds, matrix_kind="gene_tpm", use_exclude=True)
    # Even if transcript_tpm is empty/dummy in minimal, it should have the same columns
    ids_tx = get_analysis_sample_ids(ds, matrix_kind="transcript_tpm", use_exclude=True)

    assert ids_gene == ["SRR518891", "SRR518892"]
    assert ids_tx == ["SRR518891", "SRR518892"]


def test_filter_features_by_min_nonzero_samples():
    df = pd.DataFrame(
        {
            "S1": [1.0, 0.0, 0.0],
            "S2": [2.0, 0.0, 1.0],
            "S3": [3.0, 5.0, 0.0],
        },
        index=["gene_keep3", "gene_keep1", "gene_drop1"],
    )

    out = filter_features(
        df,
        min_feature_nonzero_samples=2,
        min_feature_mean=0.0,
    )

    assert "gene_keep3" in out.index
    assert "gene_drop1" not in out.index
    # gene_keep1 has 1 nonzero, so it's dropped if min=2
    assert "gene_keep1" not in out.index


def test_filter_features_by_min_feature_mean():
    df = pd.DataFrame(
        {
            "S1": [10.0, 0.1, 1.0],
            "S2": [10.0, 0.1, 1.0],
            "S3": [10.0, 0.1, 1.0],
        },
        index=["gene_high", "gene_low", "gene_mid"],
    )

    out = filter_features(
        df,
        min_feature_nonzero_samples=1,
        min_feature_mean=1.0,
    )

    assert "gene_high" in out.index
    assert "gene_mid" in out.index
    assert "gene_low" not in out.index


def test_build_analysis_matrix_applies_min_feature_mean(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["gene_tpm_path"]
    df = pd.read_csv(path)
    # Set one gene to low values
    df.loc[df["gene_id"] == "YAL001C", ["SRR518891", "SRR518892"]] = [0.01, 0.01]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    mat = build_analysis_matrix(
        ds,
        matrix_kind="gene_tpm",
        log2p1=False,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=1.0,
    )

    assert "YAL001C" not in mat.index


def test_build_analysis_matrix_raises_when_all_features_filtered(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    with pytest.raises(ValueError, match="No features remain after filtering"):
        build_analysis_matrix(
            ds,
            matrix_kind="gene_tpm",
            log2p1=False,
            use_exclude=True,
            min_feature_nonzero_samples=999,
            min_feature_mean=999999.0,
        )


def test_build_analysis_sample_table_marks_excluded_sample(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df.loc[df["sample_id"] == "SRR518892", "exclude"] = True
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    tbl = build_analysis_sample_table(
        ds,
        matrix_kind="gene_tpm",
        use_exclude=True,
    )

    included = dict(zip(tbl["sample_id"], tbl["analysis_included"]))
    assert included["SRR518891"] is True
    assert included["SRR518892"] is False
