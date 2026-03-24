from __future__ import annotations

import pandas as pd
from iwa_rnaseq_reporter.legacy.deg_preview import build_deg_preview_table


def test_compute_deg_preview_uses_only_deg_input(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    from iwa_rnaseq_reporter.legacy.deg_input import build_deg_input

    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["group"] = ["A", "B"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    deg_input = build_deg_input(ds, "gene_tpm", "group", "A", "B")

    # This should work without access to 'ds' or files
    out = build_deg_preview_table(deg_input)
    assert "rank" in out.columns
    assert "direction" in out.columns
    assert out.iloc[0]["rank"] == 1


def test_deg_preview_direction_and_rank(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset
    from iwa_rnaseq_reporter.legacy.deg_input import build_deg_input
    
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    # mock a deg_input with known values
    from iwa_rnaseq_reporter.legacy.deg_input import DEGInput
    import numpy as np
    
    # Feature 1: mean B=10, A=1 -> Up
    # Feature 2: mean B=1, A=10 -> Down
    mat = pd.DataFrame({
        "S1": [1.0, 10.0],
        "S2": [10.0, 1.0]
    }, index=["F1", "F2"])
    
    deg_input = DEGInput(
        matrix_kind="gene_tpm",
        feature_matrix=mat,
        sample_table=pd.DataFrame({"sample_id": ["S1", "S2"]}),
        group_column="group",
        group_a="A",
        group_b="B",
        group_a_samples=["S1"],
        group_b_samples=["S2"]
    )
    
    out = build_deg_preview_table(deg_input)
    
    # Check direction
    f1 = out[out["feature_id"] == "F1"].iloc[0]
    f2 = out[out["feature_id"] == "F2"].iloc[0]
    
    assert f1["direction"] == "Up"
    assert f2["direction"] == "Down"
    
    # Check rank (both have same abs log2fc in this simple mock)
    assert set(out["rank"]) == {1, 2}
