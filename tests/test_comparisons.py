from __future__ import annotations

import pandas as pd
import pytest
from src.comparisons import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_comparison_sample_table,
    validate_comparison_design,
)


def test_get_comparison_candidate_columns():
    df = pd.DataFrame(
        {
            "sample_id": ["S1", "S2", "S3"],
            "group": ["G1", "G1", "G2"],
            "batch": ["B1", "B1", "B1"], # 1 unique
            "exclude": [False, False, False],
        }
    )
    
    cands = get_comparison_candidate_columns(df)
    assert "group" in cands
    assert "batch" not in cands # because only 1 unique value
    assert "sample_id" not in cands


def test_summarize_groups():
    df = pd.DataFrame({"group": ["A", "A", "B", "C"]})
    summary = summarize_groups(df, "group")
    
    assert summary.shape[0] == 3
    # Find count for B
    count_b = summary.loc[summary["group_name"] == "B", "sample_count"].iloc[0]
    assert count_b == 1


def test_validate_comparison_design():
    # Valid
    df_valid = pd.DataFrame({"comparison_side": ["A", "A", "B", "B"]})
    assert validate_comparison_design(df_valid) == []
    
    # Invalid
    df_invalid = pd.DataFrame({"comparison_side": ["A", "B", "B"]})
    msgs = validate_comparison_design(df_invalid, min_samples_per_group=2)
    assert len(msgs) == 1
    assert "Group A" in msgs[0]
