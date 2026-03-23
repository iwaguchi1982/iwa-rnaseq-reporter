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
    Strictly filters based on 'analysis_included' samples.
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
        active_samples = sample_table.copy()
    else:
        active_samples = sample_table.loc[sample_table["analysis_included"]].copy()

    if active_samples.empty:
        return []

    candidates = []
    for col in active_samples.columns:
        if col in excluded:
            continue

        values = active_samples[col].fillna("").astype(str).str.strip()
        nonempty = values[values != ""]
        unique_vals = sorted(nonempty.unique().tolist())

        # Stricter criteria for v0.1.5:
        # 1. At least 2 groups
        # 2. Not all unique (at least some repetition)
        # 3. Sufficiently non-empty
        if len(unique_vals) >= 2 and len(unique_vals) < len(nonempty):
            candidates.append(col)

    return candidates


def summarize_groups(sample_table: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Summarize group counts for a comparison column.
    Only counts 'analysis_included' samples with non-empty group names.
    """
    if column not in sample_table.columns:
        raise ValueError(f"Column not found in sample_table: {column}")

    x = sample_table.copy()
    x[column] = x[column].fillna("").astype(str).str.strip()
    
    included = x.loc[x["analysis_included"] & (x[column] != "")].copy()

    if included.empty:
        return pd.DataFrame(columns=["group_name", "n_included"])

    summary = (
        included.groupby(column, dropna=False)
        .agg(
            n_included=("analysis_included", "count"),
        )
        .reset_index()
        .rename(columns={column: "group_name"})
        .sort_values("group_name")
        .reset_index(drop=True)
    )

    return summary


def build_group_summary(deg_input: DEGInput) -> pd.DataFrame:
    """
    UI Helper: Generate a group summary table from DEGInput.
    """
    summary = deg_input.sample_table.groupby(deg_input.group_column).agg(
        n_samples=("sample_id", "count")
    ).reset_index().rename(columns={deg_input.group_column: "group_name"})
    
    return summary.sort_values("group_name").reset_index(drop=True)


def build_comparison_sample_table(deg_input: DEGInput) -> pd.DataFrame:
    """
    UI Helper: Extract comparison sample metadata.
    Ensures columns like replicate/exclude are included if available.
    """
    cols = ["sample_id", "display_name", deg_input.group_column]
    optional = ["replicate", "batch", "exclude", "pair_id", "note"]
    
    for c in optional:
        if c in deg_input.sample_table.columns and c not in cols:
            cols.append(c)
            
    return deg_input.sample_table[cols].copy()


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
    Ensures strict alignment between matrix columns and sample records.
    """
    if group_a == group_b:
        raise ValueError("Group A and Group B must be different.")

    analysis_matrix = build_analysis_matrix(
        ds,
        matrix_kind=matrix_kind,
        log2p1=log2p1,
        use_exclude=use_exclude,
        min_feature_nonzero_samples=min_feature_nonzero_samples,
        min_feature_mean=min_feature_mean,
    )

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

    comparison_samples = analysis_sample_table.loc[
        analysis_sample_table["analysis_included"] & 
        analysis_sample_table[group_column].isin([group_a, group_b])
    ].copy()

    if comparison_samples.empty:
        raise ValueError(f"No samples matched groups '{group_a}' or '{group_b}' in the current analysis subset.")

    # Sort samples by group A first, then group B to keep things organized
    comparison_samples["_sort_group"] = comparison_samples[group_column].apply(
        lambda g: 0 if g == group_a else 1
    )
    comparison_samples = comparison_samples.sort_values(["_sort_group", "sample_id"]).drop(columns=["_sort_group"])

    selected_ids = comparison_samples["sample_id"].astype(str).tolist()

    feature_matrix = analysis_matrix.loc[:, selected_ids].copy()

    group_a_samples = comparison_samples.loc[
        comparison_samples[group_column] == group_a, "sample_id"
    ].astype(str).tolist()

    group_b_samples = comparison_samples.loc[
        comparison_samples[group_column] == group_b, "sample_id"
    ].astype(str).tolist()

    if not group_a_samples:
        raise ValueError(f"No samples found for group A: '{group_a}' in the current analysis subset.")
    if not group_b_samples:
        raise ValueError(f"No samples found for group B: '{group_b}' in the current analysis subset.")

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

    if not deg_input.group_a_samples:
        issues.append(f"No samples in group A: {deg_input.group_a}")

    if not deg_input.group_b_samples:
        issues.append(f"No samples in group B: {deg_input.group_b}")

    if len(deg_input.group_a_samples) < min_samples_per_group:
        issues.append(
            f"Group A has fewer than {min_samples_per_group} samples: {deg_input.group_a} ({len(deg_input.group_a_samples)})"
        )

    if len(deg_input.group_b_samples) < min_samples_per_group:
        issues.append(
            f"Group B has fewer than {min_samples_per_group} samples: {deg_input.group_b} ({len(deg_input.group_b_samples)})"
        )

    # Internal Alignment Checks
    matrix_ids = list(map(str, deg_input.feature_matrix.columns))
    table_ids = list(map(str, deg_input.sample_table["sample_id"]))
    combined_selected = deg_input.group_a_samples + deg_input.group_b_samples

    if matrix_ids != table_ids:
        issues.append("Internal Error: Feature matrix columns and Sample table order mismatch.")
    if set(matrix_ids) != set(combined_selected):
        issues.append("Internal Error: Feature matrix columns and selected Group IDs mismatch.")

    return issues
