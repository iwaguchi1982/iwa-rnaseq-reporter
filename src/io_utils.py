from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_json(path: str | Path) -> dict:
    """Read a JSON file and return as a dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv_indexed(path: str | Path) -> pd.DataFrame:
    """
    Read a CSV file, assuming the first column is the index.
    Expected for expression matrices.
    """
    df = pd.read_csv(path)
    if not df.empty:
        feature_col = df.columns[0]
        df = df.set_index(feature_col)
    return df


def read_csv_basic(path: str | Path) -> pd.DataFrame:
    """Read a CSV file as is."""
    return pd.read_csv(path)
