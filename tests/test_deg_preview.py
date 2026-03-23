from __future__ import annotations

import pandas as pd

from src.deg_preview import build_deg_preview_table, summarize_deg_preview


def test_build_deg_preview_table(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    from src.deg_input import build_deg_input

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
        log2p1=False,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0,
    )

    out = build_deg_preview_table(deg_input)

    assert "feature_id" in out.columns
    assert "mean_group_a" in out.columns
    assert "mean_group_b" in out.columns
    assert "log2_fc" in out.columns
    assert "abs_log2_fc" in out.columns
    assert len(out) > 0


def test_summarize_deg_preview(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    from src.deg_input import build_deg_input

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
        log2p1=False,
        use_exclude=True,
        min_feature_nonzero_samples=1,
        min_feature_mean=0.0,
    )

    preview = build_deg_preview_table(deg_input)
    summary = summarize_deg_preview(preview)

    assert "n_features" in summary
    assert "n_positive_fc" in summary
    assert "n_negative_fc" in summary
