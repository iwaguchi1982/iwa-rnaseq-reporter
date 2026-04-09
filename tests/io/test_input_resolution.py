import pytest
from pathlib import Path
import tempfile
import shutil
from iwa_rnaseq_reporter.io.input_resolution import resolve_reporter_input_paths

@pytest.fixture
def tmp_run_dir():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        results = tmpdir / "results"
        results.mkdir()
        (results / "dataset_manifest.json").write_text("{}")
        (results / "analysis_bundle_manifest.json").write_text("{}")
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)

@pytest.fixture
def tmp_flat_dir():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        (tmpdir / "dataset_manifest.json").write_text("{}")
        (tmpdir / "analysis_bundle_manifest.json").write_text("{}")
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)

def test_resolve_run_dir(tmp_run_dir):
    res = resolve_reporter_input_paths(str(tmp_run_dir))
    assert res.input_kind == "dataset_dir"
    assert res.load_mode == "dataset_plus_bundle"
    assert "dataset_manifest.json" in res.resolved_dataset_manifest_path
    assert "analysis_bundle_manifest.json" in res.resolved_bundle_manifest_path
    assert "results/" in res.resolved_dataset_manifest_path

def test_resolve_flat_dir(tmp_flat_dir):
    res = resolve_reporter_input_paths(str(tmp_flat_dir))
    assert res.input_kind == "dataset_dir"
    assert res.load_mode == "dataset_plus_bundle"
    assert "dataset_manifest.json" in res.resolved_dataset_manifest_path
    assert "analysis_bundle_manifest.json" in res.resolved_bundle_manifest_path
    assert "results/" not in res.resolved_dataset_manifest_path

def test_resolve_explicit_dataset_manifest(tmp_flat_dir):
    manifest_path = tmp_flat_dir / "dataset_manifest.json"
    res = resolve_reporter_input_paths(str(manifest_path))
    assert res.input_kind == "dataset_manifest"
    assert res.load_mode == "dataset_plus_bundle"
    assert res.resolved_dataset_manifest_path == str(manifest_path.resolve())
    assert "analysis_bundle_manifest.json" in res.resolved_bundle_manifest_path

def test_resolve_explicit_bundle_manifest(tmp_flat_dir):
    bundle_path = tmp_flat_dir / "analysis_bundle_manifest.json"
    res = resolve_reporter_input_paths(str(bundle_path))
    assert res.input_kind == "bundle_manifest"
    assert res.load_mode == "dataset_plus_bundle"
    assert res.resolved_bundle_manifest_path == str(bundle_path.resolve())
    assert "dataset_manifest.json" in res.resolved_dataset_manifest_path

def test_resolve_dataset_only(tmp_flat_dir):
    (tmp_flat_dir / "analysis_bundle_manifest.json").unlink()
    res = resolve_reporter_input_paths(str(tmp_flat_dir))
    assert res.load_mode == "dataset_only"
    assert res.resolved_bundle_manifest_path is None

def test_resolve_non_existent():
    res = resolve_reporter_input_paths("/tmp/non_existent_path_xyz")
    assert res.load_mode == "unresolved"
    assert "not exist" in res.resolution_messages[0]
