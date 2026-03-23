from __future__ import annotations

import pandas as pd
import pytest
from src.feature_stats import compute_feature_statistics, get_top_variable_features


def test_compute_feature_statistics_basic():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0, 3.0],
            "S2": [2.0, 4.0, 6.0],
        },
        index=["g1", "g2", "g3"],
    )
    
    stats = compute_feature_statistics(df)
    
    assert stats.loc["g1", "mean"] == 1.5
    assert stats.loc["g2", "nonzero_samples"] == 2
    assert stats.loc["g3", "max_value"] == 6.0


def test_get_top_variable_features():
    df = pd.DataFrame(
        {
            "S1": [1.0, 1.0, 10.0],
            "S2": [1.1, 1.0, 20.0],
        },
        index=["g1", "g2", "g3"],
    )
    # g3 has high variance, g2 has 0 variance, g1 has low variance
    
    top = get_top_variable_features(df, top_n=2)
    
    assert top.index[0] == "g3"
    assert top.index[1] == "g1"
    assert "g2" not in top.index
