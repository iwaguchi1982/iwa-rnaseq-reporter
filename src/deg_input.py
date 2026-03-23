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


def get_comparison_candidate_columns(sample_table: pd.DataFrame) -> list[str]:
    """
    Return metadata columns that are usable for comparison grouping.
    NOTE: Input should be an analysis_sample_table. 
    Only samples where 'analysis_included' is True are considered.
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

    if "analysis_included" not in sample_table.columns:
        # Fallback if called with raw metadata, but not recommended for v0.1.4
        active_samples = sample_table.copy()
    else:
        active_samples = sample_table.loc[sample_table["analysis_included"]].copy()

    candidates = []
    for col in active_samples.columns:
        if col in excluded:
            continue

        values = active_samples[col].fillna("").astype(str).str.strip()
        nonempty = values[values != ""]
        unique_vals = sorted(nonempty.unique().tolist())

        if len(unique_vals) >= 2:
            candidates.append(col)

    return candidates


def summarize_groups(sample_table: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Summarize group counts for a comparison column.
    Focuses on 'analysis_included' samples.
    """
    if column not in sample_table.columns:
        raise ValueError(f"Column not found in sample_table: {column}")

    x = sample_table.copy()
    x[column] = x[column].fillna("").astype(str).str.strip()
    
    # We only count samples that are included in analysis
    # and have a non-empty group name.
    included = x.loc[x["analysis_included"] & (x[column] != "")].copy()

    summary = (
        included.groupby(column, dropna=False)
        .agg(
            n_included=("analysis_included", "count"),
            # We could add n_total here if we want to show how many were excluded
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
    This is the Source of Truth for the DEG section.
    """
    # 1. Build the master analysis matrix
    analysis_matrix = build_analysis_matrix(
        ds,
        matrix_kind=matrix_kind,
        log2p1=log2p1,
        use_exclude=use_exclude,
        min_feature_nonzero_samples=min_feature_nonzero_samples,
        min_feature_mean=min_feature_mean,
    )

    # 2. Build the analysis sample table
    analysis_sample_table = build_analysis_sample_table(
        ds,
        matrix_kind=matrix_kind,
        use_exclude=use_exclude,
    ).copy()

    if group_column not in analysis_sample_table.columns:
        raise ValueError(f"group_column not found: {group_column}")

    analysis_sample_table[group_column] = (
        analysis_sample_table[group_column].fillna("").astype(str).str.strip()
    )

    # 3. Select samples belonging to Group A or Group B (ONLY from included samples)
    comparison_samples = analysis_sample_table.loc[
        analysis_sample_table["analysis_included"] & 
        analysis_sample_table[group_column].isin([group_a, group_b])
    ].copy()

    if comparison_samples.empty:
        raise ValueError("No samples selected for the requested comparison.")

    selected_ids = comparison_samples["sample_id"].astype(str).tolist()

    # 4. Subset matrix to the comparison samples
    # We use .loc to ensure the order of columns matches selected_ids
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

    # Internal consistency check
    expected_ids = set(deg_input.group_a_samples + deg_input.group_b_samples)
    matrix_ids = set(map(str, deg_input.feature_matrix.columns))
    table_ids = set(map(str, deg_input.sample_table["sample_id"]))
    
    if expected_ids != matrix_ids:
        issues.append("Internal Error: Feature matrix columns mismatch selected group samples.")
    if expected_ids != table_ids:
        issues.append("Internal Error: Sample table mismatch selected group samples.")

    return issues
