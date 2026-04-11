import pytest
import json
import os
import pandas as pd
from pathlib import Path
from tempfile import TemporaryDirectory
from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import (
    validate_consensus_bundle,
    read_consensus_bundle,
    EXPECTED_MANIFEST_SCHEMA
)

def _create_minimal_valid_files(root: Path):
    manifest_path = root / "consensus_manifest.json"
    handoff_path = root / "consensus_handoff_contract.json"
    csv_path = root / "consensus_decisions.csv"
    
    exec_cfg = {
        "config_name": "TestConfig", "config_version": "v1", "config_source": "test_injector",
        "ranking": {
            "overlap_weight": 0.2, "top_n_overlap_weight": 0.3, "concordance_weight": 0.2, 
            "correlation_weight": 0.3, "tie_tolerance": 0.02, "exact_tie_epsilon": 0.001
        }, 
        "consensus": {
            "consensus_margin_threshold": 0.05, "minimum_supporting_references": 1, "weak_support_mean_threshold": 0.3,
            "candidate_sort_policy": "weighted_score", "top_rank_conflict_policy": "no_consensus",
            "weak_margin_policy": "no_consensus", "insufficient_support_policy": "insufficient_evidence"
        }
    }

    manifest = {
        "schema_name": EXPECTED_MANIFEST_SCHEMA,
        "schema_version": "0.19.3",
        "generated_at": "2026-04-10T12:00:00Z",
        "consensus_run_id": "run1",
        "n_ranked_comparisons": 1,
        "n_consensus": 1,
        "n_abstain": 0,
        "n_no_consensus": 0,
        "n_insufficient_evidence": 0,
        "provenance": {
            "producer_app": "iwa_rnaseq_reporter",
            "producer_version": "0.3.0",
            "source_consensus_run_id": "run1"
        },
        "execution_config": exec_cfg
    }
    
    handoff = {
        "schema_name": "ConsensusHandoffContract",
        "schema_version": "0.19.3",
        "generated_at": "2026-04-10T12:00:00Z",
        "consensus_run_id": "run1",
        "bundle_refs": {
            "consensus_manifest_path": "consensus_manifest.json",
            "consensus_summary_path": "consensus_summary.json",
            "consensus_decisions_path": "consensus_decisions.json",
            "evidence_profiles_path": "evidence_profiles.json",
            "consensus_handoff_contract_path": "consensus_handoff_contract.json"
        },
        "included_comparison_ids": [],
        "comparison_decision_refs": [],
        "summary": {},
        "provenance": {
            "producer_app": "iwa_rnaseq_reporter",
            "producer_version": "0.3.0",
            "source_consensus_run_id": "run1"
        },
        "execution_config": exec_cfg,
        "decision_support": {
            "schema_name": "ComparatorDecisionSupportPayload",
            "schema_version": "0.19.4.1",
            "decision_evidence_refs": [],
            "summary": {
                "n_decision_refs": 0, "n_consensus": 0, "n_abstain": 0, "n_no_consensus": 0, "n_insufficient_evidence": 0
            }
        }
    }
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
    with open(handoff_path, "w") as f:
        json.dump(handoff, f)
    
    # Create the referenced dummy files
    (root / "consensus_summary.json").write_text("{}")
    (root / "consensus_decisions.json").write_text("[]")
    (root / "evidence_profiles.json").write_text("[]")
    
    csv_path.write_text("comparison_id,decision_status\nc1,consensus")
    (root / "report_summary.md").write_text("# Summary")

def test_validate_minimal_valid_bundle():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _create_minimal_valid_files(root)
            
        result = validate_consensus_bundle(root)
        if not result.is_valid:
            print([i.message for i in result.issues])
            
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
        assert "unsupported_bundle_contract" in codes

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
            
        with pytest.raises(ValueError, match="Cannot read invalid consensus bundle"):
            read_consensus_bundle(manifest_path)

def test_resolve_paths_ignores_json_corruption():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        
        # Corrupted JSON
        manifest_path.write_text("{ invalid json")
        
        # Resolver should succeed because it doesn't parse
        from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import resolve_consensus_bundle_paths
        paths = resolve_consensus_bundle_paths(manifest_path)
        assert paths.manifest_path == manifest_path
        
        # Validator should catch it
        result = validate_consensus_bundle(manifest_path)
        assert result.is_valid is False
        codes = [i.code for i in result.issues]
        assert "invalid_manifest_json" in codes

def test_validate_handoff_requirements():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        handoff_path = root / "consensus_handoff_contract.json"
        
        manifest = {
            "schema_name": EXPECTED_MANIFEST_SCHEMA,
            "schema_version": "0.19.3",
            "generated_at": "2026-04-10T12:00:00Z",
            "consensus_run_id": "r1",
            "n_ranked_comparisons": 0, "n_consensus": 0, "n_abstain": 0, "n_no_consensus": 0, "n_insufficient_evidence": 0,
            "provenance": {"producer_app": "a", "producer_version": "v1", "source_consensus_run_id": "r1"},
            "execution_config": {
                "config_name": "a", "config_version": "v1", "config_source": "b",
                "ranking": {
                    "overlap_weight": 0.2, "top_n_overlap_weight": 0.3, "concordance_weight": 0.2, 
                    "correlation_weight": 0.3, "tie_tolerance": 0.02, "exact_tie_epsilon": 0.001
                }, 
                "consensus": {
                    "consensus_margin_threshold": 0.05, "minimum_supporting_references": 1, "weak_support_mean_threshold": 0.3,
                    "candidate_sort_policy": "weighted_score", "top_rank_conflict_policy": "no_consensus",
                    "weak_margin_policy": "no_consensus", "insufficient_support_policy": "insufficient_evidence"
                }
            }
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
            
        handoff_path.write_text("{ bad handoff")
        
        result = validate_consensus_bundle(manifest_path)
        codes = [i.code for i in result.issues]
        assert "invalid_handoff_json" in codes
        # In v0.19.2a, a failing handoff parse leads to unsupported_bundle_contract
        assert "unsupported_bundle_contract" in codes

def test_validate_decision_support_requirements():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _create_minimal_valid_files(root)
        handoff_path = root / "consensus_handoff_contract.json"
        
        with open(handoff_path, "r") as f:
            handoff = json.load(f)

        # Case 1: Missing decision_support
        h_missing = handoff.copy()
        del h_missing["decision_support"]
        with open(handoff_path, "w") as f:
            json.dump(h_missing, f)
        
        res = validate_consensus_bundle(root)
        assert "missing_required_field" in [i.code for i in res.issues]

        # Case 2: Malformed summary
        h_malformed = handoff.copy()
        h_malformed["decision_support"]["summary"] = {"n_decision_refs": 0} # missing others
        with open(handoff_path, "w") as f:
            json.dump(h_malformed, f)
        
        res = validate_consensus_bundle(root)
        assert "missing_decision_support_summary_field" in [i.code for i in res.issues]

def test_validate_decision_support_consistency():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _create_minimal_valid_files(root)
        handoff_path = root / "consensus_handoff_contract.json"
        
        with open(handoff_path, "r") as f:
            handoff = json.load(f)

        # Case 1: ID mismatch
        h_mismatch = handoff.copy()
        h_mismatch["included_comparison_ids"] = ["c1"]
        h_mismatch["comparison_decision_refs"] = [{"comparison_id": "c1", "decision_status": "consensus"}]
        # decision_support remains empty []
        with open(handoff_path, "w") as f:
            json.dump(h_mismatch, f)
        
        res = validate_consensus_bundle(root)
        assert "decision_support_count_mismatch" in [i.code for i in res.issues]
        assert "decision_support_comparison_id_mismatch" in [i.code for i in res.issues]

        # Case 2: Status mismatch
        h_status = handoff.copy()
        h_status["included_comparison_ids"] = ["c1"]
        h_status["comparison_decision_refs"] = [{"comparison_id": "c1", "decision_status": "consensus"}]
        h_status["decision_support"]["decision_evidence_refs"] = [{
            "comparison_id": "c1",
            "decision_status": "abstain", # mismatch
            "reason_codes": [],
            "evidence_stats": {
                "support_margin": 0, "has_conflict": False, "has_weak_support": True,
                "n_supporting_references": 0, "n_conflicting_references": 0, "n_competing_candidates": 0
            },
            "artifact_refs": {
                "consensus_manifest_path": "consensus_manifest.json",
                "consensus_handoff_contract_path": "consensus_handoff_contract.json",
                "consensus_decisions_json_path": "consensus_decisions.json",
                "evidence_profiles_json_path": "evidence_profiles.json",
                "consensus_decisions_csv_path": "consensus_decisions.csv",
                "report_summary_md_path": "report_summary.md"
            }
        }]
        h_status["decision_support"]["summary"]["n_decision_refs"] = 1
        with open(handoff_path, "w") as f:
            json.dump(h_status, f)
        
        res = validate_consensus_bundle(root)
        assert "decision_support_status_mismatch" in [i.code for i in res.issues]

def test_validate_decision_support_artifact_ref_mismatch_all_refs():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _create_minimal_valid_files(root)
        handoff_path = root / "consensus_handoff_contract.json"

        with open(handoff_path, "r") as f:
            handoff = json.load(f)

        handoff["included_comparison_ids"] = ["c1", "c2"]
        handoff["comparison_decision_refs"] = [
            {"comparison_id": "c1", "decision_status": "consensus"},
            {"comparison_id": "c2", "decision_status": "no_consensus"},
        ]

        good_art_refs = {
            "consensus_manifest_path": "consensus_manifest.json",
            "consensus_handoff_contract_path": "consensus_handoff_contract.json",
            "consensus_decisions_json_path": "consensus_decisions.json",
            "evidence_profiles_json_path": "evidence_profiles.json",
            "consensus_decisions_csv_path": "consensus_decisions.csv",
            "report_summary_md_path": "report_summary.md",
        }

        bad_art_refs = {
            "consensus_manifest_path": "consensus_manifest.json",
            "consensus_handoff_contract_path": "consensus_handoff_contract.json",
            "consensus_decisions_json_path": "WRONG_decisions.json",
            "evidence_profiles_json_path": "WRONG_profiles.json",
            "consensus_decisions_csv_path": "consensus_decisions.csv",
            "report_summary_md_path": "report_summary.md",
        }

        handoff["decision_support"]["decision_evidence_refs"] = [
            {
                "comparison_id": "c1",
                "decision_status": "consensus",
                "reason_codes": [],
                "evidence_stats": {
                    "support_margin": 0.1,
                    "has_conflict": False,
                    "has_weak_support": False,
                    "n_supporting_references": 1,
                    "n_conflicting_references": 0,
                    "n_competing_candidates": 0,
                },
                "artifact_refs": good_art_refs,
            },
            {
                "comparison_id": "c2",
                "decision_status": "no_consensus",
                "reason_codes": [],
                "evidence_stats": {
                    "support_margin": 0.0,
                    "has_conflict": True,
                    "has_weak_support": False,
                    "n_supporting_references": 1,
                    "n_conflicting_references": 1,
                    "n_competing_candidates": 1,
                },
                "artifact_refs": bad_art_refs,
            },
        ]
        handoff["decision_support"]["summary"]["n_decision_refs"] = 2
        handoff["decision_support"]["summary"]["n_consensus"] = 1
        handoff["decision_support"]["summary"]["n_no_consensus"] = 1

        with open(handoff_path, "w") as f:
            json.dump(handoff, f)

        res = validate_consensus_bundle(root)
        codes = [i.code for i in result.issues] if 'result' in locals() else [i.code for i in res.issues]
        assert "decision_support_artifact_ref_mismatch" in codes

        mismatch_fields = [
            i.field_name for i in res.issues
            if i.code == "decision_support_artifact_ref_mismatch"
        ]
        assert any("decision_evidence_refs[1].artifact_refs.consensus_decisions_json_path" in f for f in mismatch_fields)
        assert any("decision_evidence_refs[1].artifact_refs.evidence_profiles_json_path" in f for f in mismatch_fields)

def test_validate_decision_support_top_refs_validation():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        _create_minimal_valid_files(root)
        handoff_path = root / "consensus_handoff_contract.json"

        with open(handoff_path, "r") as f:
            handoff = json.load(f)

        handoff["included_comparison_ids"] = ["c1"]
        handoff["comparison_decision_refs"] = [
            {"comparison_id": "c1", "decision_status": "consensus"}
        ]

        handoff["decision_support"]["decision_evidence_refs"] = [
            {
                "comparison_id": "c1",
                "decision_status": "consensus",
                "reason_codes": [],
                "evidence_stats": {
                    "support_margin": 0.1,
                    "has_conflict": False,
                    "has_weak_support": False,
                    "n_supporting_references": 1,
                    "n_conflicting_references": 0,
                    "n_competing_candidates": 0,
                },
                "artifact_refs": {
                    "consensus_manifest_path": "consensus_manifest.json",
                    "consensus_handoff_contract_path": "consensus_handoff_contract.json",
                    "consensus_decisions_json_path": "consensus_decisions.json",
                    "evidence_profiles_json_path": "evidence_profiles.json",
                    "consensus_decisions_csv_path": "consensus_decisions.csv",
                    "report_summary_md_path": "report_summary.md",
                },
                # わざと不正
                "top_supporting_reference_refs": {"bad": "shape"},
                "top_conflicting_reference_refs": [
                    {"reference_dataset_id": "DS_ONLY"}
                ],
            }
        ]
        handoff["decision_support"]["summary"]["n_decision_refs"] = 1
        handoff["decision_support"]["summary"]["n_consensus"] = 1

        with open(handoff_path, "w") as f:
            json.dump(handoff, f)

        res = validate_consensus_bundle(root)
        codes = [i.code for i in res.issues]

        assert "invalid_top_reference_refs_type" in codes
        assert "missing_top_reference_ref_field" in codes
