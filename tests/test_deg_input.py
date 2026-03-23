from __future__ import annotations

import pandas as pd
import pytest

from src.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
)


def test_get_comparison_candidate_columns(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["ctrl", "treated"]
    df["condition"] = ["ctrl", "treated"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    cols = get_comparison_candidate_columns(ds.sample_metadata)

    assert "group" in cols
    assert "condition" in cols
    assert "sample_id" not in cols
    assert "exclude" not in cols


def test_summarize_groups(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    from src.analysis import build_analysis_sample_table

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["ctrl", "treated"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    tbl = build_analysis_sample_table(ds, matrix_kind="gene_tpm", use_exclude=True)
    summary = summarize_groups(tbl, "group")

    assert "group_name" in summary.columns
    assert "n_samples" in summary.columns
    assert summary["group_name"].tolist() == ["ctrl", "treated"]


def test_build_deg_input(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["ctrl", "treated"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    deg_input = build_deg_input(
        ds,
        matrix_kind="gene_tpm",
        group_column="group",
        group_a="ctrl",
        group_b="treated",
        log2p1=True,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0,
    )

    assert deg_input.group_column == "group"
    assert deg_input.group_a_samples == ["SRR518891"]
    assert deg_input.group_b_samples == ["SRR518892"]
    assert list(deg_input.feature_matrix.columns) == ["SRR518891", "SRR518892"]


def test_validate_deg_input_warns_small_groups(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["ctrl", "treated"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    deg_input = build_deg_input(
        ds,
        matrix_kind="gene_tpm",
        group_column="group",
        group_a="ctrl",
        group_b="treated",
        log2p1=True,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0,
    )

    issues = validate_deg_input(deg_input, min_samples_per_group=2)
    assert any("fewer than 2 samples" in x for x in issues)
