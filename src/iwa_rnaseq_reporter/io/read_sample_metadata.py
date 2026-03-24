from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


REQUIRED_COLUMNS = [
    "specimen_id",
    "subject_id",
    "group_labels",
]

RECOMMENDED_COLUMNS = [
    "visit_id",
    "sample_name",
    "timepoint_label",
    "batch_label",
    "pairing_id",
    "include_flag",
    "note",
]


@dataclass
class SampleMetadataRow:
    specimen_id: str
    subject_id: str
    visit_id: Optional[str] = None
    sample_name: Optional[str] = None
    group_labels: Optional[str] = None
    timepoint_label: Optional[str] = None
    batch_label: Optional[str] = None
    pairing_id: Optional[str] = None
    include_flag: bool = True
    note: Optional[str] = None


def parse_bool(value: object, default: bool = True) -> bool:
    """Safely parse boolean-like values from CSV/pandas."""
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return default

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    if text == "":
        return default

    raise ValueError(f"Invalid boolean value for include_flag: {value!r}")


def _normalize_optional(value: object) -> Optional[str]:
    """Convert NaN/empty values to None, otherwise return stripped string."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def load_sample_metadata_df(csv_path: str | Path) -> pd.DataFrame:
    """Load sample metadata CSV as DataFrame and validate required columns."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"sample metadata CSV not found: {path}")

    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"sample metadata CSV is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Normalize required string columns
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].map(_normalize_optional)

    # Required columns must not be empty
    for col in REQUIRED_COLUMNS:
        empty_mask = df[col].isna()
        if empty_mask.any():
            bad_rows = list(df.index[empty_mask])
            raise ValueError(
                f"sample metadata column '{col}' contains empty values at rows: {bad_rows}"
            )

    # Optional columns: add if missing
    for col in RECOMMENDED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Normalize optional string columns
    optional_text_cols = [
        "visit_id",
        "sample_name",
        "group_labels",
        "timepoint_label",
        "batch_label",
        "pairing_id",
        "note",
    ]
    for col in optional_text_cols:
        df[col] = df[col].map(_normalize_optional)

    # include_flag normalization
    df["include_flag"] = df["include_flag"].map(lambda v: parse_bool(v, default=True))

    # specimen_id uniqueness
    if df["specimen_id"].duplicated().any():
        duplicated = df.loc[df["specimen_id"].duplicated(), "specimen_id"].tolist()
        raise ValueError(
            f"sample metadata contains duplicated specimen_id values: {duplicated}"
        )

    return df


def load_sample_metadata_rows(csv_path: str | Path) -> List[SampleMetadataRow]:
    """Load sample metadata CSV and return validated row objects."""
    df = load_sample_metadata_df(csv_path)

    rows: List[SampleMetadataRow] = []
    for _, r in df.iterrows():
        rows.append(
            SampleMetadataRow(
                specimen_id=str(r["specimen_id"]),
                subject_id=str(r["subject_id"]),
                visit_id=r["visit_id"],
                sample_name=r["sample_name"],
                group_labels=r["group_labels"],
                timepoint_label=r["timepoint_label"],
                batch_label=r["batch_label"],
                pairing_id=r["pairing_id"],
                include_flag=bool(r["include_flag"]),
                note=r["note"],
            )
        )
    return rows
