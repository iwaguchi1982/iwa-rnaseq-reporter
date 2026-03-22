from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import ValidationMessage

if TYPE_CHECKING:
    import pandas as pd


def validate_manifest_raw_legacy(manifest: dict) -> list[ValidationMessage]:
    """Validate the raw manifest dictionary against legacy v0.1.7 rules."""
    messages = []
    required_keys = ["app_name", "run_name"]
    for key in required_keys:
        if key not in manifest:
            messages.append(
                ValidationMessage(
                    level="fatal",
                    code="manifest_missing_key",
                    message=f"Manifest is missing required top-level key: {key}",
                )
            )

    files = manifest.get("files") or manifest.get("paths")
    if not files:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="manifest_missing_file_config",
                message="Manifest is missing 'files' or 'paths' configuration.",
            )
        )
    else:
        required_files = [
            "sample_metadata",
            "sample_qc_summary",
            "gene_tpm",
            "gene_numreads",
            "run_summary",
        ]
        for f in required_files:
            if f not in files:
                messages.append(
                    ValidationMessage(
                        level="fatal",
                        code="manifest_missing_file_key",
                        message=f"Manifest is missing required file entry: {f}",
                    )
                )

    return messages


def validate_required_files(resolved_paths: dict[str, Path]) -> list[ValidationMessage]:
    """Check if the required files actually exist on disk."""
    messages = []
    required = [
        "sample_metadata",
        "sample_qc_summary",
        "gene_tpm",
        "gene_numreads",
        "run_summary",
    ]
    optional = ["transcript_tpm", "transcript_numreads"]

    for key in required:
        path = resolved_paths.get(key)
        if not path or not path.exists():
            messages.append(
                ValidationMessage(
                    level="fatal",
                    code="missing_required_file",
                    message=f"Required file not found: {key} ({path})",
                )
            )

    for key in optional:
        path = resolved_paths.get(key)
        if not path or not path.exists():
            messages.append(
                ValidationMessage(
                    level="warning",
                    code="missing_optional_file",
                    message=f"Optional file not found: {key} ({path})",
                )
            )

    return messages


def validate_sample_metadata(df: pd.DataFrame) -> list[ValidationMessage]:
    """Validate sample metadata DataFrame."""
    messages = []
    if "sample_id" not in df.columns:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="metadata_missing_sample_id",
                message="Sample metadata is missing 'sample_id' column.",
            )
        )
    return messages


def validate_sample_qc_summary(df: pd.DataFrame) -> list[ValidationMessage]:
    """Validate sample QC summary DataFrame."""
    messages = []
    if "sample_id" not in df.columns:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="qc_missing_sample_id",
                message="Sample QC summary is missing 'sample_id' column.",
            )
        )
    return messages


def validate_expression_matrix(
    df: pd.DataFrame, matrix_label: str
) -> list[ValidationMessage]:
    """Validate an expression matrix (e.g., TPM or read counts)."""
    messages = []
    if df.empty:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="empty_matrix",
                message=f"Expression matrix '{matrix_label}' is empty.",
            )
        )
    if len(df.columns) == 0:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="matrix_no_sample_columns",
                message=f"Expression matrix '{matrix_label}' has no sample columns.",
            )
        )
    return messages


def validate_matrix_pair(
    matrix1: pd.DataFrame, matrix2: pd.DataFrame
) -> list[ValidationMessage]:
    """Ensure two matrices have the same sample columns."""
    messages = []
    if list(matrix1.columns) != list(matrix2.columns):
        messages.append(
            ValidationMessage(
                level="fatal",
                code="matrix_sample_mismatch",
                message="Sample columns do not match between matrices.",
            )
        )
    return messages


def validate_sample_id_consistency(
    sample_metadata: pd.DataFrame,
    sample_qc_summary: pd.DataFrame,
    gene_tpm: pd.DataFrame,
    run_summary: dict,
) -> list[ValidationMessage]:
    """Check consistency of sample IDs across all data sources."""
    messages = []
    matrix_samples = set(gene_tpm.columns)
    metadata_samples = set(sample_metadata["sample_id"])
    qc_samples = set(sample_qc_summary.get("sample_id", []))

    # Matrix samples MUST be in metadata
    missing_in_metadata = matrix_samples - metadata_samples
    if missing_in_metadata:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="matrix_ids_missing_in_metadata",
                message=f"Samples in matrix missing from metadata: {sorted(list(missing_in_metadata))}",
            )
        )

    # Matrix samples SHOULD be in QC (maybe not fatal depending on needs, but spec says "should be in qc summary")
    # Spec 7.2.B says "gene matrix にある sample は qc summary に存在すべき"
    missing_in_qc = matrix_samples - qc_samples
    if missing_in_qc:
        messages.append(
            ValidationMessage(
                level="fatal",
                code="matrix_ids_missing_in_qc",
                message=f"Samples in matrix missing from QC summary: {sorted(list(missing_in_qc))}",
            )
        )

    # Extra in metadata is a warning
    extra_in_metadata = metadata_samples - matrix_samples
    if extra_in_metadata:
        messages.append(
            ValidationMessage(
                level="warning",
                code="extra_metadata_samples",
                message=f"Samples in metadata not present in matrix: {sorted(list(extra_in_metadata))}",
            )
        )

    return messages
