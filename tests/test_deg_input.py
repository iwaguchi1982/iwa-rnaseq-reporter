from __future__ import annotations

import pandas as pd
import pytest

from iwa_rnaseq_reporter.legacy.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
    build_group_summary,
    build_comparison_sample_table
)


def test_get_comparison_candidate_columns_filters_all_unique(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    from iwa_rnaseq_reporter.legacy.analysis import build_analysis_sample_table

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    # create a column with all unique values
    df["unique_col"] = ["u1", "u2"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    tbl = build_analysis_sample_table(ds, matrix_kind="gene_tpm", use_exclude=True)
    cols = get_comparison_candidate_columns(tbl)

    # 'unique_col' should be filtered out because len(unique) == len(nonempty)
    assert "unique_col" not in cols


def test_build_deg_input_aligns_feature_matrix_rows_and_cols(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["B", "A"] # intentionally swapped to check sorting
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    deg_input = build_deg_input(ds, "gene_tpm", "group", "A", "B")

    # In my logic, I sorting by group (A then B)
    assert list(deg_input.sample_table["sample_id"]) == ["SRR518892", "SRR518891"]
    assert list(deg_input.feature_matrix.columns) == ["SRR518892", "SRR518891"]
    assert deg_input.group_a_samples == ["SRR518892"]
    assert deg_input.group_b_samples == ["SRR518891"]


def test_build_deg_input_respects_exclude(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["A", "B"]
    df.loc[df["sample_id"] == "SRR518891", "exclude"] = True
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    
    with pytest.raises(ValueError, match="No samples found for group"):
        build_deg_input(ds, "gene_tpm", "group", "A", "B", use_exclude=True)


def test_build_deg_input_raises_for_same_group(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    with pytest.raises(ValueError, match="must be different"):
        build_deg_input(ds, "gene_tpm", "group", "A", "A")


def test_ui_helpers(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["A", "B"]
    df.to_csv(path, index=False)
    
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    deg_input = build_deg_input(ds, "gene_tpm", "group", "A", "B")
    
    summary = build_group_summary(deg_input)
    assert "group_name" in summary.columns
    assert list(summary["group_name"]) == ["A", "B"]
    
    sample_table = build_comparison_sample_table(deg_input)
    assert "sample_id" in sample_table.columns
    assert "group" in sample_table.columns
    assert len(sample_table) == 2
