from __future__ import annotations

import pandas as pd
import pytest

from src.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
)


def test_get_comparison_candidate_columns_depends_on_analysis_included(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    from src.analysis import build_analysis_sample_table

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    # metadata has 2 groups
    df["group"] = ["ctrl", "treated"]
    # but one is excluded!
    df.loc[df["sample_id"] == "SRR518892", "exclude"] = True
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    
    # If we respect exclude, only 1 sample (ctrl) is included.
    tbl = build_analysis_sample_table(ds, matrix_kind="gene_tpm", use_exclude=True)
    cols = get_comparison_candidate_columns(tbl)

    # In active samples, 'group' only has 'ctrl' -> not a candidate!
    assert "group" not in cols


def test_summarize_groups_filters_empty_and_excluded(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    from src.analysis import build_analysis_sample_table

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    # 2 samples, but one is excluded
    df["group"] = ["ctrl", ""]
    df.loc[df["sample_id"] == "SRR518892", "exclude"] = True
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    tbl = build_analysis_sample_table(ds, matrix_kind="gene_tpm", use_exclude=True)
    summary = summarize_groups(tbl, "group")

    # Should only contain 'ctrl'
    assert summary["group_name"].tolist() == ["ctrl"]
    assert summary.loc[summary["group_name"] == "ctrl", "n_included"].iloc[0] == 1


def test_build_deg_input_internal_consistency(minimal_dataset_files):
    from src.loader import load_reporter_dataset

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["A", "B"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    deg_input = build_deg_input(
        ds,
        matrix_kind="gene_tpm",
        group_column="group",
        group_a="A",
        group_b="B",
    )

    # Check that matrix columns match sample_table row order exactly
    assert list(deg_input.feature_matrix.columns) == list(deg_input.sample_table["sample_id"])
    assert set(deg_input.group_a_samples) == {"SRR518891"}
    assert set(deg_input.group_b_samples) == {"SRR518892"}


def test_validate_deg_input_errors(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    # Mock a broken deg_input
    from src.deg_input import DEGInput
    import numpy as np
    
    broken = DEGInput(
        matrix_kind="gene_tpm",
        feature_matrix=pd.DataFrame(columns=["S1"]), 
        sample_table=pd.DataFrame({"sample_id": ["S2"]}), # Mismatch!
        group_column="group",
        group_a="A",
        group_b="B",
        group_a_samples=["S1"],
        group_b_samples=[]
    )
    
    issues = validate_deg_input(broken)
    assert any("mismatch" in x.lower() for x in issues)
    assert any("no samples in group b" in x.lower() for x in issues)
