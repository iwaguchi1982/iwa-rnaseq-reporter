import pytest
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import (
    validate_consensus_bundle,
    read_consensus_bundle,
    EXPECTED_MANIFEST_SCHEMA
)

def test_validate_minimal_valid_bundle():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        handoff_path = root / "consensus_handoff_contract.json"
        
        manifest = {
            "consensus_run_id": "run1",
            "n_ranked_comparisons": 1,
            "n_consensus": 1,
            "n_abstain": 0,
            "n_no_consensus": 0,
            "n_insufficient_evidence": 0,
            "schema_name": EXPECTED_MANIFEST_SCHEMA,
            "schema_version": "0.19.1",
            "generated_at": "2026-04-10T12:00:00Z",
            "provenance": {
                "producer_app": "iwa_rnaseq_reporter",
                "producer_version": "0.3.0",
                "source_consensus_run_id": "run1"
            }
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
        with open(handoff_path, "w") as f:
            json.dump({"schema_name": "ConsensusHandoffContract"}, f)
            
        result = validate_consensus_bundle(manifest_path)
        assert result.is_valid is True
        assert result.error_count == 0

def test_validate_missing_required_fields():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        
        # Manifest missing schema_name and provenance
        manifest = {
            "consensus_run_id": "run1"
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
            
        result = validate_consensus_bundle(manifest_path)
        assert result.is_valid is False
        assert result.error_count > 0
        codes = [i.code for i in result.issues]
        assert "missing_required_field" in codes
        assert "unsupported_schema" in codes

def test_read_bundle_failure_on_unsupported_schema():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        
        manifest = {
            "schema_name": "WrongSchema",
            "schema_version": "0.1.0"
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
            
        with pytest.raises(ValueError, match="Unsupported consensus bundle schema"):
            read_consensus_bundle(manifest_path)
