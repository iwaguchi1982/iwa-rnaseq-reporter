from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.deg_input import DEGInput
from src.deg_stats import compute_statistical_deg


def test_compute_statistical_deg_basic():
    # Synthetic data: 
    # Gene 1: Up in B (A=1, B=10)
    # Gene 2: Down in B (A=10, B=1)
    # Gene 3: No change (A=5, B=5)
    
    mat = pd.DataFrame({
        "A1": [1.0, 10.0, 5.0],
        "A2": [1.1, 10.1, 5.1],
        "B1": [10.0, 1.0, 5.0],
        "B2": [10.1, 1.1, 5.1],
    }, index=["G_UP", "G_DOWN", "G_NC"])
    
    deg_input = DEGInput(
        matrix_kind="gene_tpm",
        feature_matrix=mat,
        sample_table=pd.DataFrame({"sample_id": ["A1", "A2", "B1", "B2"]}),
        group_column="group",
        group_a="A",
        group_b="B",
        group_a_samples=["A1", "A2"],
        group_b_samples=["B1", "B2"]
    )
    
    res = compute_statistical_deg(deg_input)
    df = res.result_table
    
    # Check G_UP
    up = df[df["feature_id"] == "G_UP"].iloc[0]
    assert up["direction"] == "Up"
    assert up["p_value"] < 0.05
    
    # Check G_DOWN
    down = df[df["feature_id"] == "G_DOWN"].iloc[0]
    assert down["direction"] == "Down"
    assert down["p_value"] < 0.05
    
    # Check G_NC
    nc = df[df["feature_id"] == "G_NC"].iloc[0]
    assert nc["p_value"] > 0.05
    
    assert res.n_features_tested == 3
    assert "padj" in df.columns
    assert "rank_by_padj" in df.columns


def test_compute_statistical_deg_handles_nan_and_zero_var():
    mat = pd.DataFrame({
        "A1": [np.nan, 5.0],
        "A2": [np.nan, 5.0],
        "B1": [1.0, 5.0],
        "B2": [1.0, 5.0],
    }, index=["G_NAN", "G_ZEROVAR"])
    
    deg_input = DEGInput(
        matrix_kind="gene_tpm",
        feature_matrix=mat,
        sample_table=pd.DataFrame({"sample_id": ["A1", "A2", "B1", "B2"]}),
        group_column="group",
        group_a="A",
        group_b="B",
        group_a_samples=["A1", "A2"],
        group_b_samples=["B1", "B2"]
    )
    
    res = compute_statistical_deg(deg_input)
    df = res.result_table
    
    # G_NAN should have NaN p_value
    nan_gene = df[df["feature_id"] == "G_NAN"].iloc[0]
    assert np.isnan(nan_gene["p_value"])
    
    # G_ZEROVAR should have NaN p_value (ttest failure due to no variance)
    # Actually scipy ttest returns NaN if variance is zero and means are equal
    zv_gene = df[df["feature_id"] == "G_ZEROVAR"].iloc[0]
    assert np.isnan(zv_gene["p_value"])
