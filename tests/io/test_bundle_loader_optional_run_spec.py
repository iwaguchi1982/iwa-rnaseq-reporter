import pytest
import json
import shutil
from pathlib import Path
from iwa_rnaseq_reporter.io.bundle_loader import load_reporter_analysis_bundle

def test_load_bundle_without_execution_run_spec(tmp_path):
    # Setup: Create a bundle directory without execution-run.spec.json
    bundle_dir = tmp_path / "test_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "specs").mkdir()
    (bundle_dir / "results").mkdir()
    (bundle_dir / "logs").mkdir()
    
    # 1. Create Matrix Spec
    matrix_spec = {
        "$schema_name": "MatrixSpec",
        "schema_version": "0.1.0",
        "matrix_id": "MAT_001",
        "matrix_kind": "count_matrix",
        "matrix_path": "results/counts.tsv",
        "metadata": {
            "feature_count": 10,
            "sample_count": 2,
            "sample_axis_kind": "column"
        }
    }
    with open(bundle_dir / "specs" / "matrix.spec.json", "w") as f:
        json.dump(matrix_spec, f)
        
    # 2. Create Dummy Matrix File
    with open(bundle_dir / "results" / "counts.tsv", "w") as f:
        f.write("feature_id\ts1\ts2\nf1\t10\t20\n")
        
    # 3. Create Manifest WITHOUT execution_run_spec
    manifest = {
        "schema_name": "AnalysisBundleManifest",
        "schema_version": "0.1.0",
        "bundle_id": "B_001",
        "artifacts": {
            "matrix_spec": "specs/matrix.spec.json",
            "merged_matrix": "results/counts.tsv",
            "analysis_merge_summary": "specs/analysis_summary.json",
            "aligned_sample_metadata": "results/sample_metadata.tsv",
            "build_analysis_matrix_log": "logs/build.log"
        },
        "contract_name": "analysis_bundle",
        "contract_version": "1.0.0",
        "bundle_kind": "rna_seq_analysis_bundle",
        "producer": "iwa-rnaseq-counter",
        "producer_version": "0.8.0"
    }
    manifest_path = bundle_dir / "results" / "analysis_bundle_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
        
    # Create remaining dummy files to satisfy the reader
    with open(bundle_dir / "specs" / "analysis_summary.json", "w") as f:
        json.dump({"matrix_id": "MAT_001", "column_order_specimen_ids": ["s1", "s2"]}, f)
    with open(bundle_dir / "results" / "sample_metadata.tsv", "w") as f:
        f.write("specimen_id\ns1\ns2\n")
    with open(bundle_dir / "logs" / "build.log", "w") as f:
        f.write("log")

    # TEST: Load bundle
    # We need to make sure iwa-rnaseq-counter is in path
    import sys
    import os
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(repo_root / "iwa_rnaseq_counter" / "src"))
    sys.path.insert(0, str(repo_root / "iwa_rnaseq_reporter" / "src"))
    
    bundle_view = load_reporter_analysis_bundle(str(manifest_path))
    
    assert bundle_view.matrix_id == "MAT_001"
    assert bundle_view.run_id == "UNKNOWN"  # Correctly defaulted
    assert bundle_view.producer == "iwa-rnaseq-counter"
