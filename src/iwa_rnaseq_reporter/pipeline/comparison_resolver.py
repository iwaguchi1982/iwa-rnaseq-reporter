from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

from iwa_rnaseq_reporter.io.read_sample_metadata import load_sample_metadata_df
from iwa_rnaseq_reporter.models.comparison import ComparisonSpec
from iwa_rnaseq_reporter.models.matrix import MatrixSpec
from iwa_rnaseq_reporter.models.resolved_comparison import ResolvedComparisonPlan


@dataclass
class ResolvedGroup:
    label: str
    specimen_ids: List[str]
    subject_ids: List[str]
    matrix_columns: List[str]


def _ensure_two_group_comparison(comparison_spec: ComparisonSpec) -> None:
    if comparison_spec.comparison_type != "two_group":
        raise NotImplementedError(
            f"Only comparison_type='two_group' is supported in v0.1, "
            f"got: {comparison_spec.comparison_type!r}"
        )

    if len(comparison_spec.groups) != 2:
        raise ValueError(
            f"two_group comparison requires exactly 2 groups, "
            f"got: {len(comparison_spec.groups)}"
        )


def _normalize_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def evaluate_criteria(df: pd.DataFrame, criteria: Dict[str, Any]) -> pd.Series:
    """
    Minimal rule evaluator for v0.1.
    Supported keys:
      - specimen_id
      - subject_id
      - group_labels
      - timepoint_label
      - batch_label
      - include_flag
    All criteria are combined with AND.
    Values are interpreted as 'column value in values'.
    """
    if not criteria:
        return pd.Series([True] * len(df), index=df.index)

    supported_keys = {
        "specimen_id",
        "subject_id",
        "group_labels",
        "timepoint_label",
        "batch_label",
        "include_flag",
    }

    unknown = set(criteria.keys()) - supported_keys
    if unknown:
        raise NotImplementedError(
            f"Unsupported criteria keys in v0.1: {sorted(unknown)}"
        )

    mask = pd.Series([True] * len(df), index=df.index)

    for key, raw_values in criteria.items():
        values = _normalize_values(raw_values)

        if key == "include_flag":
            # For include_flag, support true/false string style as well
            normalized = []
            for v in values:
                lowered = v.lower()
                if lowered in {"true", "1", "yes", "y", "on"}:
                    normalized.append(True)
                elif lowered in {"false", "0", "no", "n", "off"}:
                    normalized.append(False)
                else:
                    raise ValueError(f"Invalid include_flag criteria value: {v!r}")
            mask &= df[key].isin(normalized)
        else:
            mask &= df[key].isin(values)

    return mask


def _apply_sample_selector(df: pd.DataFrame, comparison_spec: ComparisonSpec) -> pd.DataFrame:
    """
    v0.1 minimal selector handling.
    For now:
      - inclusion/exclusion must be empty, otherwise error
    """
    selector = comparison_spec.sample_selector
    if selector.inclusion or selector.exclusion:
        raise NotImplementedError(
            "ComparisonSpec.sample_selector is not implemented yet in v0.1"
        )
    return df


def _resolve_group(
    df: pd.DataFrame,
    matrix_columns: List[str],
    label: str,
    criteria: Dict[str, Any],
) -> ResolvedGroup:
    group_df = df.loc[evaluate_criteria(df, criteria)].copy()

    specimen_ids = group_df["specimen_id"].tolist()
    subject_ids = group_df["subject_id"].tolist()

    missing_in_matrix = [sid for sid in specimen_ids if sid not in matrix_columns]
    if missing_in_matrix:
        raise ValueError(
            f"Resolved group '{label}' contains specimen_ids not found in matrix columns: "
            f"{missing_in_matrix}"
        )

    matrix_cols = [sid for sid in specimen_ids if sid in matrix_columns]

    return ResolvedGroup(
        label=label,
        specimen_ids=specimen_ids,
        subject_ids=subject_ids,
        matrix_columns=matrix_cols,
    )


def resolve_comparison_plan(
    matrix_spec: MatrixSpec,
    comparison_spec: ComparisonSpec,
    matrix_df: pd.DataFrame,
) -> ResolvedComparisonPlan:
    """
    Resolve MatrixSpec + ComparisonSpec + sample metadata into a concrete execution plan.
    """
    if comparison_spec.input_matrix_id != matrix_spec.matrix_id:
        raise ValueError(
            f"ComparisonSpec.input_matrix_id ({comparison_spec.input_matrix_id}) "
            f"does not match MatrixSpec.matrix_id ({matrix_spec.matrix_id})"
        )

    _ensure_two_group_comparison(comparison_spec)

    sample_metadata_path = matrix_spec.metadata.get("sample_metadata_path")
    if not sample_metadata_path:
        raise ValueError(
            "MatrixSpec.metadata.sample_metadata_path is required for comparison resolution"
        )

    sample_df = load_sample_metadata_df(sample_metadata_path)

    # Apply include_flag first
    sample_df = sample_df.loc[sample_df["include_flag"] == True].copy()

    # Apply sample_selector (currently only checks unsupported use)
    sample_df = _apply_sample_selector(sample_df, comparison_spec)

    matrix_columns = [str(c) for c in matrix_df.columns.tolist()]

    group_a_spec = comparison_spec.groups[0]
    group_b_spec = comparison_spec.groups[1]

    group_a = _resolve_group(
        df=sample_df,
        matrix_columns=matrix_columns,
        label=group_a_spec.label,
        criteria=group_a_spec.criteria,
    )
    group_b = _resolve_group(
        df=sample_df,
        matrix_columns=matrix_columns,
        label=group_b_spec.label,
        criteria=group_b_spec.criteria,
    )

    if not group_a.matrix_columns:
        raise ValueError(f"Resolved group '{group_a.label}' has no samples found in matrix")
    if not group_b.matrix_columns:
        raise ValueError(f"Resolved group '{group_b.label}' has no samples found in matrix")

    overlap = set(group_a.specimen_ids) & set(group_b.specimen_ids)
    if overlap:
        raise ValueError(
            f"Resolved groups overlap. specimen_ids present in both groups: {sorted(overlap)}"
        )

    included_specimen_ids = sorted(set(group_a.specimen_ids + group_b.specimen_ids))
    excluded_specimen_ids = sorted(
        set(sample_df["specimen_id"].tolist()) - set(included_specimen_ids)
    )

    return ResolvedComparisonPlan(
        comparison_id=comparison_spec.comparison_id,
        input_matrix_id=matrix_spec.matrix_id,
        comparison_type=comparison_spec.comparison_type,
        analysis_intent=comparison_spec.analysis_intent,

        group_a_label=group_a.label,
        group_a_specimen_ids=group_a.specimen_ids,

        group_b_label=group_b.label,
        group_b_specimen_ids=group_b.specimen_ids,

        paired=comparison_spec.paired,
        covariates=comparison_spec.covariates,

        group_a_subject_ids=group_a.subject_ids,
        group_b_subject_ids=group_b.subject_ids,

        group_a_matrix_columns=group_a.matrix_columns,
        group_b_matrix_columns=group_b.matrix_columns,

        sample_axis=matrix_spec.sample_axis,
        feature_type=matrix_spec.feature_type,
        normalization=matrix_spec.normalization,

        matrix_path=matrix_spec.matrix_path,
        feature_annotation_path=matrix_spec.feature_annotation_path,
        sample_metadata_path=str(sample_metadata_path),

        included_specimen_ids=included_specimen_ids,
        excluded_specimen_ids=excluded_specimen_ids,

        metadata={
            "matrix_scope": matrix_spec.matrix_scope,
            "source_assay_ids": matrix_spec.source_assay_ids,
            "source_specimen_ids": matrix_spec.source_specimen_ids,
            "source_subject_ids": matrix_spec.source_subject_ids,
        },
    )
