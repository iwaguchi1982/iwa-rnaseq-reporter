from __future__ import annotations

import pandas as pd


def get_comparison_candidate_columns(sample_metadata: pd.DataFrame) -> list[str]:
    """
    Return columns that are likely useful for group comparisons.
    Filters out obvious non-grouping columns like sample_id, note, etc.
    """
    black_list = {"sample_id", "display_name", "exclude", "note", "pair_id", "color"}
    candidates = [c for c in sample_metadata.columns if c not in black_list]
    
    # Filter further: columns that have more than 1 unique value
    final = []
    for c in candidates:
        if sample_metadata[c].nunique(dropna=True) > 1:
            final.append(c)
            
    return final


def summarize_groups(sample_metadata: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Summarize sample counts per group in the specified column.
    """
    if column not in sample_metadata.columns:
        return pd.DataFrame()
        
    counts = sample_metadata[column].value_counts(dropna=False).rename_axis("group_name").reset_index(name="sample_count")
    return counts


def build_comparison_sample_table(
    sample_metadata: pd.DataFrame,
    column: str,
    group_a: str,
    group_b: str,
    use_exclude: bool = True,
) -> pd.DataFrame:
    """
    Return a table of samples belonging to either Group A or Group B.
    """
    md = sample_metadata.copy()
    md["sample_id"] = md["sample_id"].astype(str)
    
    if "exclude" in md.columns and use_exclude:
        md = md.loc[~md["exclude"]].copy()
        
    if column not in md.columns:
        return pd.DataFrame()
        
    # Group labeling
    md["comparison_side"] = None
    md.loc[md[column].astype(str) == str(group_a), "comparison_side"] = "A"
    md.loc[md[column].astype(str) == str(group_b), "comparison_side"] = "B"
    
    subset = md.loc[md["comparison_side"].notnull()].copy()
    
    # Sorting for convenience
    subset = subset.sort_values(["comparison_side", "sample_id"])
    
    return subset


def validate_comparison_design(
    comparison_sample_table: pd.DataFrame,
    min_samples_per_group: int = 2,
) -> list[str]:
    """
    Check if the comparison design is valid for DEG.
    """
    messages = []
    
    if comparison_sample_table.empty:
        return ["No samples selected for comparison."]
        
    counts = comparison_sample_table["comparison_side"].value_counts()
    count_a = counts.get("A", 0)
    count_b = counts.get("B", 0)
    
    if count_a < min_samples_per_group:
        messages.append(f"Group A has only {count_a} sample(s), need at least {min_samples_per_group}.")
    if count_b < min_samples_per_group:
        messages.append(f"Group B has only {count_b} sample(s), need at least {min_samples_per_group}.")
        
    return messages
