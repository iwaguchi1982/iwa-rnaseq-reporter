from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from ..models.comparison import ComparisonSpec
from ..models.matrix import MatrixSpec

@dataclass(frozen=True)
class ComparisonSpecValidationIssue:
    level: str  # "error" | "warning"
    code: str
    message: str
    field: Optional[str] = None
    group_label: Optional[str] = None

@dataclass
class ComparisonSpecValidationResult:
    is_valid: bool
    error_count: int
    warning_count: int
    issues: List[ComparisonSpecValidationIssue] = field(default_factory=list)

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return f"ComparisonSpec Validation {status}: {self.error_count} errors, {self.warning_count} warnings."

def _append_issue(
    issues: List[ComparisonSpecValidationIssue],
    level: str,
    code: str,
    message: str,
    field: Optional[str] = None,
    group_label: Optional[str] = None,
):
    issues.append(ComparisonSpecValidationIssue(level, code, message, field, group_label))

def validate_comparison_spec(
    comparison_spec: ComparisonSpec,
    matrix_spec: Optional[MatrixSpec] = None
) -> ComparisonSpecValidationResult:
    """
    Performs lightweight static validation on ComparisonSpec before resolution.
    Optionally checks consistency with MatrixSpec if provided.
    """
    issues: List[ComparisonSpecValidationIssue] = []

    # 1. Comparison Type and Structure
    if comparison_spec.comparison_type != "two_group":
        _append_issue(
            issues, "error", "unsupported_comparison_type",
            f"Only 'two_group' is supported, got: {comparison_spec.comparison_type!r}",
            field="comparison_type"
        )

    if len(comparison_spec.groups) != 2:
        _append_issue(
            issues, "error", "invalid_group_count",
            f"Two-group comparison requires exactly 2 groups, got: {len(comparison_spec.groups)}",
            field="groups"
        )

    # 2. Group Labels and Criteria
    labels = []
    for i, group in enumerate(comparison_spec.groups):
        label = group.label.strip()
        if not label:
            _append_issue(
                issues, "error", "empty_group_label",
                f"Group at index {i} has an empty label",
                field=f"groups[{i}].label"
            )
        else:
            if label in labels:
                _append_issue(
                    issues, "error", "duplicate_group_label",
                    f"Duplicate group label: {label!r}",
                    field="groups", group_label=label
                )
            labels.append(label)

        if not group.criteria:
            _append_issue(
                issues, "error", "empty_group_criteria",
                f"Group {label!r} has no criteria defined",
                field="groups", group_label=label
            )
        else:
            supported_keys = {
                "specimen_id", "subject_id", "group_labels", 
                "timepoint_label", "batch_label", "include_flag",
            }
            unknown = set(group.criteria.keys()) - supported_keys
            if unknown:
                _append_issue(
                    issues, "error", "unsupported_criteria_keys",
                    f"Unsupported criteria keys for group {label!r}: {sorted(unknown)}",
                    field="groups", group_label=label
                )
            
            # Check for effectively empty criteria values
            for key, val in group.criteria.items():
                is_empty = False
                if val is None:
                    is_empty = True
                elif isinstance(val, str):
                    if not val.strip():
                        is_empty = True
                elif isinstance(val, list):
                    # Filter out effectively empty strings/Nones
                    normalized = [str(v).strip() for v in val if v is not None and str(v).strip()]
                    if not normalized:
                        is_empty = True
                
                if is_empty:
                    _append_issue(
                        issues, "error", "empty_criteria_value",
                        f"Criteria {key!r} for group {label!r} has an effectively empty value: {val!r}",
                        field="groups", group_label=label
                    )

    # 3. Unsupported Features (Fail-fast to prevent silent no-op)
    if comparison_spec.sample_selector:
        if comparison_spec.sample_selector.inclusion or comparison_spec.sample_selector.exclusion:
            _append_issue(
                issues, "error", "unsupported_sample_selector",
                "sample_selector (inclusion/exclusion) is not yet implemented",
                field="sample_selector"
            )

    if comparison_spec.paired:
        _append_issue(
            issues, "error", "unsupported_paired_analysis",
            "paired=True analysis is not yet implemented in the current engine",
            field="paired"
        )

    if comparison_spec.covariates:
        # Check for non-empty list
        _append_issue(
            issues, "error", "unsupported_covariates",
            f"Covariates are not yet supported in the current engine, got: {comparison_spec.covariates}",
            field="covariates"
        )

    # 4. Cross-Spec Consistency and Required Fields
    if not comparison_spec.input_matrix_id:
        _append_issue(
            issues, "error", "missing_input_matrix_id",
            "ComparisonSpec.input_matrix_id is required",
            field="input_matrix_id"
        )
    elif matrix_spec:
        if comparison_spec.input_matrix_id != matrix_spec.matrix_id:
            _append_issue(
                issues, "error", "matrix_id_mismatch",
                f"ComparisonSpec.input_matrix_id ({comparison_spec.input_matrix_id}) "
                f"does not match MatrixSpec.matrix_id ({matrix_spec.matrix_id})",
                field="input_matrix_id"
            )

    error_count = sum(1 for i in issues if i.level == "error")
    warning_count = sum(1 for i in issues if i.level == "warning")

    return ComparisonSpecValidationResult(
        is_valid=(error_count == 0),
        error_count=error_count,
        warning_count=warning_count,
        issues=issues
    )
