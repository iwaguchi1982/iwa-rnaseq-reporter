from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_matrix_csv(path: Path, index_name: str, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out.index.name = index_name
    out.reset_index().to_csv(path, index=False)


@pytest.fixture
def sample_ids() -> list[str]:
    return ["SRR518891", "SRR518892"]


@pytest.fixture
def base_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "yeast_run_014"
    (run_dir / "results").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture
def minimal_dataset_files(base_run_dir: Path, sample_ids: list[str]) -> dict[str, Path]:
    run_dir = base_run_dir
    results_dir = run_dir / "results"

    sample_metadata = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "group": ["ctrl", "treated"],
            "condition": ["ctrl", "treated"],
            "replicate": ["1", "1"],
            "batch": ["", ""],
            "pair_id": ["", ""],
            "note": ["", ""],
            "display_name": sample_ids,
            "color": ["", ""],
            "exclude": [False, False],
        }
    )

    sample_qc_summary = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "num_processed": [9350778, 11534226],
            "mapping_rate": [0.7233, 1.6517],
        }
    )

    gene_tpm = pd.DataFrame(
        {
            "SRR518891": [10.0, 20.0, 30.0],
            "SRR518892": [11.0, 21.0, 31.0],
        },
        index=["YAL001C", "YAL002W", "YAL003W"],
    )

    gene_numreads = pd.DataFrame(
        {
            "SRR518891": [100, 200, 300],
            "SRR518892": [110, 210, 310],
        },
        index=["YAL001C", "YAL002W", "YAL003W"],
    )

    transcript_tpm = pd.DataFrame(
        {
            "SRR518891": [1.0, 2.0, 3.0],
            "SRR518892": [1.1, 2.1, 3.1],
        },
        index=["YAL001C_T1", "YAL002W_T1", "YAL003W_T1"],
    )

    transcript_numreads = pd.DataFrame(
        {
            "SRR518891": [10, 20, 30],
            "SRR518892": [11, 21, 31],
        },
        index=["YAL001C_T1", "YAL002W_T1", "YAL003W_T1"],
    )

    run_summary = {
        "analysis_name": "yeast_run_014",
        "run_name": "yeast_run_014",
        "sample_count": 2,
        "success_count": 2,
        "failure_count": 0,
        "sample_ids_all": sample_ids,
        "sample_ids_success": sample_ids,
        "sample_ids_failed": [],
        "sample_ids_aggregated": sample_ids,
        "input_source": "auto_detect",
        "sample_metadata_columns": [
            "group",
            "condition",
            "replicate",
            "batch",
            "pair_id",
            "note",
            "display_name",
            "color",
            "exclude",
        ],
        "sample_metadata_columns_nonempty": ["display_name"],
        "transcript_rows": 3,
        "gene_rows": 3,
        "outputs": [
            {
                "sample_id": "SRR518891",
                "is_success": True,
            },
            {
                "sample_id": "SRR518892",
                "is_success": True,
            },
        ],
        "quantifier": "salmon",
        "quantifier_version": "1.10.1",
        "strandedness": {
            "mode": "unstranded",
            "confidence": "high",
        },
        "threads": 4,
    }

    dataset_manifest = {
        "app_name": "iwa-rnaseq-counter",
        "app_version": "v0.1.7",
        "run_name": "yeast_run_014",
        "analysis_name": "yeast_run_014",
        "input_source": "auto_detect",
        "quantifier": "salmon",
        "quantifier_version": "1.10.1",
        "sample_count_total": 2,
        "sample_count_success": 2,
        "sample_count_failed": 0,
        "sample_ids_all": sample_ids,
        "sample_ids_success": sample_ids,
        "sample_ids_failed": [],
        "sample_ids_aggregated": sample_ids,
        "files": {
            "sample_metadata": "sample_metadata.csv",
            "sample_qc_summary": "sample_qc_summary.csv",
            "transcript_tpm": "transcript_tpm.csv",
            "transcript_numreads": "transcript_numreads.csv",
            "gene_tpm": "gene_tpm.csv",
            "gene_numreads": "gene_numreads.csv",
            "run_summary": "run_summary.json",
            "sample_sheet": "../sample_sheet.csv",
            "run_config": "../run_config.json",
            "run_log": "../logs/run.log",
        },
    }

    _write_csv(results_dir / "sample_metadata.csv", sample_metadata)
    _write_csv(results_dir / "sample_qc_summary.csv", sample_qc_summary)
    _write_matrix_csv(results_dir / "gene_tpm.csv", "gene_id", gene_tpm)
    _write_matrix_csv(results_dir / "gene_numreads.csv", "gene_id", gene_numreads)
    _write_matrix_csv(results_dir / "transcript_tpm.csv", "transcript_id", transcript_tpm)
    _write_matrix_csv(
        results_dir / "transcript_numreads.csv", "transcript_id", transcript_numreads
    )
    _write_json(results_dir / "run_summary.json", run_summary)
    _write_json(results_dir / "dataset_manifest.json", dataset_manifest)

    (run_dir / "sample_sheet.csv").write_text("sample_id\n", encoding="utf-8")
    _write_json(run_dir / "run_config.json", {"dummy": True})
    (run_dir / "logs" / "run.log").write_text("test log\n", encoding="utf-8")

    return {
        "run_dir": run_dir,
        "results_dir": results_dir,
        "manifest_path": results_dir / "dataset_manifest.json",
        "run_summary_path": results_dir / "run_summary.json",
        "sample_metadata_path": results_dir / "sample_metadata.csv",
        "sample_qc_summary_path": results_dir / "sample_qc_summary.csv",
        "gene_tpm_path": results_dir / "gene_tpm.csv",
        "gene_numreads_path": results_dir / "gene_numreads.csv",
        "transcript_tpm_path": results_dir / "transcript_tpm.csv",
        "transcript_numreads_path": results_dir / "transcript_numreads.csv",
    }
