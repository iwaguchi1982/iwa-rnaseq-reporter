import os
import tempfile
import pytest
import json
import zipfile
from iwa_rnaseq_reporter.app.comparator_review_import_builder import read_review_bundle

def test_validate_missing_artifact():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf_path = tf.name
        
    try:
        # Create ZIP without review_rows.csv
        with zipfile.ZipFile(tf_path, "w") as zf:
            zf.writestr("review_manifest.json", "{}")
            zf.writestr("review_handoff_contract.json", "{}")
            
        imp_ctx = read_review_bundle(tf_path)
        assert not imp_ctx.is_valid
        assert any("Missing required artifact: review_rows.csv" in issue for issue in imp_ctx.issues)
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)

def test_validate_schema_mismatch():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf_path = tf.name
        
    try:
        with zipfile.ZipFile(tf_path, "w") as zf:
            zf.writestr("review_manifest.json", json.dumps({"schema_name": "wrong-schema", "provenance": {}}))
            zf.writestr("review_handoff_contract.json", json.dumps({"schema_name": "wrong-handoff", "provenance": {}}))
            zf.writestr("review_rows.json", "[]")
            zf.writestr("review_rows.csv", "")
            zf.writestr("review_summary.json", "{}")
            zf.writestr("review_summary.md", "")
            
        imp_ctx = read_review_bundle(tf_path)
        assert not imp_ctx.is_valid
        assert any("Invalid manifest schema_name" in issue for issue in imp_ctx.issues)
        assert any("Invalid handoff schema_name" in issue for issue in imp_ctx.issues)
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)

def test_validate_id_mismatch():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf_path = tf.name
        
    try:
        manifest = {
            "schema_name": "comparator-review-export-manifest",
            "provenance": {},
            "source_consensus_run_id": "run1"
        }
        handoff = {
            "schema_name": "comparator-review-handoff",
            "schema_version": "1.0.0",
            "generated_at": "2024-01-01T00:00:00",
            "review_run_id": "rev1",
            "provenance": {},
            "source_consensus_run_id": "run1",
            "included_comparison_ids": ["comp1"],
            "review_decision_refs": [], # Mismatch
            "bundle_refs": {"review_bundle_filename": "rev1.zip"},
            "source_refs": {"source_consensus_run_id": "run1"},
            "summary": {"n_total_rows": 0}
        }
        
        with zipfile.ZipFile(tf_path, "w") as zf:
            zf.writestr("review_manifest.json", json.dumps(manifest))
            zf.writestr("review_handoff_contract.json", json.dumps(handoff))
            zf.writestr("review_rows.json", "[]")
            zf.writestr("review_rows.csv", "")
            zf.writestr("review_summary.json", json.dumps({"n_total_rows": 0}))
            zf.writestr("review_summary.md", "")
            
        imp_ctx = read_review_bundle(tf_path)
        assert not imp_ctx.is_valid, f"Issues: {imp_ctx.issues}"
        assert any("count mismatch" in issue for issue in imp_ctx.issues), f"Expected 'count mismatch', got: {imp_ctx.issues}"
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
