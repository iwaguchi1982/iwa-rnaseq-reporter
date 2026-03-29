from __future__ import annotations

from pathlib import Path
import pandas as pd

from .io_utils import read_json, read_csv_basic, read_csv_indexed
from .manifest import load_manifest, resolve_manifest_paths
from .models import ReporterDataset, ValidationMessage
from .normalizers import (
    normalize_expression_matrix,
    normalize_sample_metadata,
    normalize_sample_qc_summary,
)
from .validators import (
    validate_expression_matrix,
    validate_manifest_raw_legacy,
    validate_matrix_pair,
    validate_required_files,
    validate_sample_id_consistency,
    validate_sample_metadata,
    validate_sample_qc_summary,
)


class ReporterLoadError(Exception):
    def __init__(self, messages: list[ValidationMessage]):
        self.messages = messages
        super().__init__("Failed to load reporter dataset due to fatal errors.")


def load_reporter_dataset(manifest_path: str | Path) -> ReporterDataset:
    """
    Main entry point to load a dataset.
    Performs full validation and normalization.
    Supports file path or directory path (auto-resolves manifest).
    """
    # 0. Existence check
    input_path = Path(manifest_path)
    if not input_path.exists():
        raise ReporterLoadError(
            [
                ValidationMessage(
                    level="fatal",
                    code="path_not_found",
                    message=f"The provided path does not exist: {input_path}",
                )
            ]
        )

    actual_manifest_path = input_path
    input_type = "manifest"

    # Auto-resolve if directory
    if input_path.is_dir():
        if (input_path / "results" / "dataset_manifest.json").exists():
            actual_manifest_path = input_path / "results" / "dataset_manifest.json"
            input_type = "run_dir"
        elif (input_path / "dataset_manifest.json").exists():
            actual_manifest_path = input_path / "dataset_manifest.json"
            input_type = "results_dir"
        else:
            raise ReporterLoadError(
                [
                    ValidationMessage(
                        level="fatal",
                        code="manifest_not_found",
                        message=f"Could not find dataset_manifest.json in {input_path} or {input_path}/results/",
                    )
                ]
            )

    messages: list[ValidationMessage] = []

    # 1. Manifest
    manifest = load_manifest(actual_manifest_path)
    messages += validate_manifest_raw_legacy(manifest)

    # 2. Path resolution
    resolved = resolve_manifest_paths(manifest, actual_manifest_path)
    messages += validate_required_files(resolved)

    # Stop if we can't find required files
    if any(m.level == "fatal" for m in messages):
        raise ReporterLoadError(messages)

    # 3. Read Files
    run_summary = read_json(resolved["run_summary"])
    raw_metadata = read_csv_basic(resolved["sample_metadata"])
    raw_qc = read_csv_basic(resolved["sample_qc_summary"])
    raw_gene_tpm = read_csv_indexed(resolved["gene_tpm"])
    raw_gene_numreads = read_csv_indexed(resolved["gene_numreads"])

    # 4. Normalize
    sample_metadata = normalize_sample_metadata(raw_metadata)
    sample_qc_summary = normalize_sample_qc_summary(raw_qc)
    gene_tpm = normalize_expression_matrix(raw_gene_tpm)
    gene_numreads = normalize_expression_matrix(raw_gene_numreads)

    # Optional files
    transcript_tpm = None
    transcript_numreads = None
    feature_annotation = None

    if resolved.get("transcript_tpm") and resolved["transcript_tpm"].exists():
        transcript_tpm = normalize_expression_matrix(
            read_csv_indexed(resolved["transcript_tpm"])
        )
    if resolved.get("transcript_numreads") and resolved["transcript_numreads"].exists():
        transcript_numreads = normalize_expression_matrix(
            read_csv_indexed(resolved["transcript_numreads"])
        )

    # Load feature_annotation if available
    # Check manifest first, then auto-resolve
    fa_path = resolved.get("feature_annotation")
    
    # Standard v0.5.0 results structure: results/feature_annotation.tsv
    # manifest is at results/dataset_manifest.json
    results_dir = actual_manifest_path.parent
    base_dir = results_dir.parent

    if not fa_path or not fa_path.exists():
        # Fallback to auto-discovery in results_dir or base_dir
        if (results_dir / "feature_annotation.tsv").exists():
            fa_path = results_dir / "feature_annotation.tsv"
        elif (base_dir / "feature_annotation.tsv").exists():
            fa_path = base_dir / "feature_annotation.tsv"
    
    if fa_path and fa_path.exists():
        # Update resolved for tracking
        resolved["feature_annotation"] = fa_path
        try:
            # feature_annotation is typically a TSV or CSV
            sep = "\t" if fa_path.suffix == ".tsv" else ","
            feature_annotation = pd.read_csv(fa_path, sep=sep)
            # Ensure v0.5.0 contract: feature_id must exist
            if "feature_id" not in feature_annotation.columns:
                messages.append(ValidationMessage(
                    level="warning",
                    code="annotation_invalid",
                    message="feature_annotation.tsv lacks 'feature_id' column. Ignoring annotation file."
                ))
                feature_annotation = None
            elif "gene_symbol" not in feature_annotation.columns:
                messages.append(ValidationMessage(
                    level="warning",
                    code="annotation_incomplete",
                    message="feature_annotation.tsv lacks 'gene_symbol' column. Symbols will be unavailable."
                ))
                # Keep it anyway, maybe other columns are useful later, but display_label will fallback
        except Exception as e:
            messages.append(ValidationMessage(
                level="warning",
                code="annotation_load_error",
                message=f"Failed to load feature_annotation: {e}"
            ))

    # 5. Validation after reading
    messages += validate_sample_metadata(sample_metadata)
    messages += validate_sample_qc_summary(sample_qc_summary)
    messages += validate_expression_matrix(gene_tpm, "gene_tpm")
    messages += validate_expression_matrix(gene_numreads, "gene_numreads")
    messages += validate_matrix_pair(gene_tpm, gene_numreads)

    # Consistency checks
    messages += validate_sample_id_consistency(
        sample_metadata, sample_qc_summary, gene_tpm, run_summary
    )

    if any(m.level == "fatal" for m in messages):
        raise ReporterLoadError(messages)

    # Final construction
    # Use resolved absolute path for manifest_path to ensure base_dir/results_dir consistency
    actual_manifest_path = actual_manifest_path.resolve()

    return ReporterDataset(
        dataset_id=manifest.get("analysis_name") or manifest.get("run_name", "unknown"),
        run_name=manifest.get("run_name", "unknown"),
        input_type=input_type,
        manifest_path=actual_manifest_path,
        base_dir=actual_manifest_path.parent.parent,
        results_dir=actual_manifest_path.parent,
        manifest=manifest,
        run_summary=run_summary,
        resolved_paths=resolved,
        sample_metadata=sample_metadata,
        sample_qc_summary=sample_qc_summary,
        gene_tpm=gene_tpm,
        gene_numreads=gene_numreads,
        feature_annotation=feature_annotation,
        transcript_tpm=transcript_tpm,
        transcript_numreads=transcript_numreads,
        sample_ids_all=run_summary.get("sample_ids_all", []),
        sample_ids_success=run_summary.get("sample_ids_success", []),
        sample_ids_failed=run_summary.get("sample_ids_failed", []),
        sample_ids_aggregated=run_summary.get("sample_ids_aggregated", []),
        messages=messages,
    )
