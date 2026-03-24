from __future__ import annotations

import pandas as pd
import pytest

from iwa_rnaseq_reporter.legacy.loader import ReporterLoadError, load_reporter_dataset


def _codes(messages) -> list[str]:
    return [m.code for m in messages]


def test_load_reporter_dataset_success(minimal_dataset_files):
    manifest_path = minimal_dataset_files["manifest_path"]

    ds = load_reporter_dataset(manifest_path)

    assert ds.run_name == "yeast_run_014"
    assert ds.dataset_id == "yeast_run_014"
    assert ds.analysis_name == "yeast_run_014"

    assert ds.app_name == "iwa-rnaseq-counter"
    assert ds.app_version == "v0.1.7"

    assert ds.sample_ids_all == ["SRR518891", "SRR518892"]
    assert ds.sample_ids_success == ["SRR518891", "SRR518892"]
    assert ds.sample_ids_failed == []
    assert ds.sample_ids_aggregated == ["SRR518891", "SRR518892"]

    assert list(ds.gene_tpm.columns) == ["SRR518891", "SRR518892"]
    assert list(ds.gene_numreads.columns) == ["SRR518891", "SRR518892"]
    assert list(ds.sample_metadata["sample_id"]) == ["SRR518891", "SRR518892"]
    assert list(ds.sample_qc_summary["sample_id"]) == ["SRR518891", "SRR518892"]

    assert ds.transcript_tpm is not None
    assert ds.transcript_numreads is not None
    assert not ds.has_fatal


def test_load_reporter_dataset_missing_optional_transcript_files_warns(
    minimal_dataset_files,
):
    minimal_dataset_files["transcript_tpm_path"].unlink()
    minimal_dataset_files["transcript_numreads_path"].unlink()

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    assert ds.transcript_tpm is None
    assert ds.transcript_numreads is None

    codes = _codes(ds.messages)
    assert "missing_optional_file" in codes
    assert not ds.has_fatal


def test_load_reporter_dataset_missing_required_sample_metadata_raises(
    minimal_dataset_files,
):
    minimal_dataset_files["sample_metadata_path"].unlink()

    with pytest.raises(ReporterLoadError) as excinfo:
        load_reporter_dataset(minimal_dataset_files["manifest_path"])

    codes = _codes(excinfo.value.messages)
    assert "missing_required_file" in codes


def test_load_reporter_dataset_extra_metadata_sample_warns(minimal_dataset_files):
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "sample_id": "SRR999999",
                        "group": "extra",
                        "condition": "extra",
                        "replicate": "1",
                        "batch": "",
                        "pair_id": "",
                        "note": "",
                        "display_name": "SRR999999",
                        "color": "",
                        "exclude": False,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    codes = _codes(ds.messages)
    assert "extra_metadata_samples" in codes
    assert not ds.has_fatal


def test_load_reporter_dataset_gene_matrices_sample_mismatch_is_fatal(
    minimal_dataset_files,
):
    path = minimal_dataset_files["gene_numreads_path"]
    df = pd.read_csv(path)
    df = df.rename(columns={"SRR518892": "SRR518892_X"})
    df.to_csv(path, index=False)

    with pytest.raises(ReporterLoadError) as excinfo:
        load_reporter_dataset(minimal_dataset_files["manifest_path"])

    codes = _codes(excinfo.value.messages)
    assert "matrix_sample_mismatch" in codes


def test_load_reporter_dataset_matrix_sample_missing_in_metadata_is_fatal(
    minimal_dataset_files,
):
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df = df[df["sample_id"] != "SRR518892"]
    df.to_csv(path, index=False)

    with pytest.raises(ReporterLoadError) as excinfo:
        load_reporter_dataset(minimal_dataset_files["manifest_path"])

    codes = _codes(excinfo.value.messages)
    assert "matrix_ids_missing_in_metadata" in codes


def test_load_reporter_dataset_display_name_is_filled_from_sample_id(
    minimal_dataset_files,
):
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["display_name"] = ["", None]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    assert list(ds.sample_metadata["display_name"]) == ["SRR518891", "SRR518892"]


def test_load_reporter_dataset_condition_is_filled_from_group(minimal_dataset_files):
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["condition"] = ["", ""]
    df["group"] = ["ctrl", "treated"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    assert list(ds.sample_metadata["condition"]) == ["ctrl", "treated"]


def test_load_reporter_dataset_exclude_is_normalized_to_bool(minimal_dataset_files):
    path = minimal_dataset_files["sample_metadata_path"]
    df = pd.read_csv(path)
    df["exclude"] = ["TRUE", "0"]
    df.to_csv(path, index=False)

    ds = load_reporter_dataset(minimal_dataset_files["manifest_path"])

    assert list(ds.sample_metadata["exclude"]) == [True, False]


def test_load_reporter_dataset_run_dir_sets_actual_manifest_path(minimal_dataset_files):
    run_dir = minimal_dataset_files["run_dir"]

    ds = load_reporter_dataset(run_dir)

    assert ds.input_type == "run_dir"
    assert ds.manifest_path == minimal_dataset_files["manifest_path"].resolve()
    assert ds.results_dir == minimal_dataset_files["results_dir"].resolve()
    assert ds.base_dir == run_dir.resolve()
