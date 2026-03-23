from __future__ import annotations

import pandas as pd
import pytest
from src.gene_search import search_features, build_feature_profile_table


def test_search_features_basic():
    idx = pd.Index(["YAL001C", "YAL002W", "YBL001C", "ACT1"])
    
    assert search_features(idx, "YAL") == ["YAL001C", "YAL002W"]
    assert search_features(idx, "001") == ["YAL001C", "YBL001C"]
    assert search_features(idx, "act") == ["ACT1"]
    assert search_features(idx, "missing") == []


def test_build_feature_profile_table(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    
    # YAL001C is present in the minimal dataset
    profile = build_feature_profile_table(ds, "YAL001C", log2p1=False)
    
    assert isinstance(profile, pd.DataFrame)
    assert "expression_value" in profile.columns
    assert "sample_id" in profile.columns
    assert "group" in profile.columns
    assert profile.shape[0] == 2
    assert profile["sample_id"].tolist() == ["SRR518891", "SRR518892"]


def test_build_feature_profile_table_raises_on_missing(minimal_dataset_files):
    from src.loader import load_reporter_dataset
    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    
    with pytest.raises(ValueError, match="not found"):
        build_feature_profile_table(ds, "NON_EXISTENT")
