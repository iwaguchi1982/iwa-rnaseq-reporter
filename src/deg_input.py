from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from .analysis import build_analysis_matrix, build_analysis_sample_table


@dataclass
class DEGInput:
    matrix_kind: str
    feature_matrix: pd.DataFrame          # rows=features, cols=selected samples
    sample_table: pd.DataFrame            # sample_id, comparison labels, metadata...
    group_column: str
    group_a: str
    group_b: str
    group_a_samples: list[str]
    group_b_samples: list[str]


def get_comparison_candidate_columns(sample_metadata: pd.DataFrame) -> list[str]:
    """
    Return metadata columns that are usable for comparison grouping.
    Excludes technical/helper columns and columns with <2 non-empty unique values.
    """
    excluded = {
        "sample_id",
        "display_name",
        "exclude",
        "analysis_included",
        "note",
        "color",
        "pair_id",
    }

    candidates = []
    for col in sample_metadata.columns:
        if col in excluded:
            continue

        values = sample_metadata[col].fillna("").astype(str).str.strip()
        nonempty = values[values != ""]
        unique_vals = sorted(nonempty.unique().tolist())

        if len(unique_vals) >= 2:
            candidates.append(col)

    return candidates


def summarize_groups(sample_table: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Summarize group counts for a comparison column.
    """
    if column not in sample_table.columns:
        raise ValueError(f"Column not found in sample_table: {column}")

    x = sample_table.copy()
    x[column] = x[column].fillna("").astype(str).str.strip()
    x = x.loc[x[column] != ""].copy()

    summary = (
        x.groupby(column, dropna=False)
        .agg(
            n_samples=("sample_id", "count"),
            n_excluded=("exclude", lambda s: int(s.sum()) if "exclude" in x.columns else 0),
            n_included=("analysis_included", lambda s: int(s.sum()) if "analysis_included" in x.columns else 0),
        )
        .reset_index()
        .rename(columns={column: "group_name"})
        .sort_values("group_name")
        .reset_index(drop=True)
    )

    return summary


def build_deg_input(
    ds,
    matrix_kind: str,
    group_column: str,
    group_a: str,
    group_b: str,
    log2p1: bool = True,
    use_exclude: bool = True,
    min_feature_nonzero_samples: int = 1,
    min_feature_mean: float = 0.0,
) -> DEGInput:
    """
    Build a comparison-ready DEGInput object from current dataset settings.
    """
    analysis_matrix = build_analysis_matrix(
        ds,
        matrix_kind=matrix_kind,
        log2p1=log2p1,
        use_exclude=use_exclude,
        min_feature_nonzero_samples=min_feature_nonzero_samples,
        min_feature_mean=min_feature_mean,
    )

    sample_table = build_analysis_sample_table(
        ds,
        matrix_kind=matrix_kind,
        use_exclude=use_exclude,
    ).copy()

    if group_column not in sample_table.columns:
        raise ValueError(f"group_column not found: {group_column}")

    sample_table[group_column] = sample_table[group_column].fillna("").astype(str).str.strip()

    comparison_samples = sample_table.loc[
        sample_table["analysis_included"] & sample_table[group_column].isin([group_a, group_b])
    ].copy()

    if comparison_samples.empty:
        raise ValueError("No samples selected for the requested comparison.")

    selected_ids = comparison_samples["sample_id"].astype(str).tolist()

    feature_matrix = analysis_matrix.loc[:, selected_ids].copy()

    group_a_samples = comparison_samples.loc[
        comparison_samples[group_column] == group_a, "sample_id"
    ].astype(str).tolist()

    group_b_samples = comparison_samples.loc[
        comparison_samples[group_column] == group_b, "sample_id"
    ].astype(str).tolist()

    return DEGInput(
        matrix_kind=matrix_kind,
        feature_matrix=feature_matrix,
        sample_table=comparison_samples,
        group_column=group_column,
        group_a=group_a,
        group_b=group_b,
        group_a_samples=group_a_samples,
        group_b_samples=group_b_samples,
    )


def validate_deg_input(
    deg_input: DEGInput,
    min_samples_per_group: int = 2,
) -> list[str]:
    """
    Return human-readable validation issues for DEG input.
    Empty list means 'ready enough' for preview.
    """
    issues: list[str] = []

    if deg_input.feature_matrix.empty:
        issues.append("Feature matrix is empty.")

    if len(deg_input.group_a_samples) == 0:
        issues.append(f"No samples in group A: {deg_input.group_a}")

    if len(deg_input.group_b_samples) == 0:
        issues.append(f"No samples in group B: {deg_input.group_b}")

    if len(deg_input.group_a_samples) < min_samples_per_group:
        issues.append(
            f"Group A has fewer than {min_samples_per_group} samples: {deg_input.group_a} ({len(deg_input.group_a_samples)})"
        )

    if len(deg_input.group_b_samples) < min_samples_per_group:
        issues.append(
            f"Group B has fewer than {min_samples_per_group} samples: {deg_input.group_b} ({len(deg_input.group_b_samples)})"
        )

    expected = set(deg_input.group_a_samples + deg_input.group_b_samples)
    actual = set(map(str, deg_input.feature_matrix.columns))
    if expected != actual:
        issues.append("Feature matrix columns do not match selected comparison samples.")

    return issues
