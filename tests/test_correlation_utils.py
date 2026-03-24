from __future__ import annotations

import pandas as pd
import pytest

from iwa_rnaseq_reporter.legacy.correlation_utils import (
    build_sample_annotation_table,
    compute_sample_correlation,
)


def test_compute_sample_correlation_basic():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0, 3.0],
            "S2": [2.0, 3.0, 4.0],
            "S3": [10.0, 11.0, 12.0],
        },
        index=["g1", "g2", "g3"],
    )

    corr = compute_sample_correlation(df)

    assert corr.shape == (3, 3)
    assert list(corr.index) == ["S1", "S2", "S3"]
    assert list(corr.columns) == ["S1", "S2", "S3"]
    # Diagonal should be 1.0
    assert corr.loc["S1", "S1"] == pytest.approx(1.0)


def test_compute_sample_correlation_requires_two_samples():
    df = pd.DataFrame(
        {
            "S1": [1.0, 2.0, 3.0],
        },
        index=["g1", "g2", "g3"],
    )

    with pytest.raises(ValueError, match="at least 2 samples"):
        compute_sample_correlation(df)


def test_build_sample_annotation_table(minimal_dataset_files):
    from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])
    ann = build_sample_annotation_table(ds, ["SRR518891", "SRR518892"])

    assert "sample_id" in ann.columns
    assert "display_name" in ann.columns
    assert ann["sample_id"].tolist() == ["SRR518891", "SRR518892"]
