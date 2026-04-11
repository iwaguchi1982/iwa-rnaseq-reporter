import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_consensus_import import (
    ConsensusBundleImportContext,
    ConsensusBundlePaths,
    ConsensusBundleContractInfo
)
from iwa_rnaseq_reporter.app.comparator_review_session_builder import build_comparator_review_session_context

def test_build_review_session_from_healthy_import():
    """
    Verify that a healthy import context (with decision_support) 
    correctly generates normalized review rows.
    Corresponds to spec 6-1, 6-2, 6-3.
    """
    handoff = {
        "consensus_run_id": "run123",
        "included_comparison_ids": ["C1", "C2"],
        "decided_label_keys": ["TUMOR", "NORMAL"],
        "decision_support": {
            "decision_evidence_refs": [
                {
                    "comparison_id": "C1",
                    "decision_status": "consensus",
                    "decided_label_key": "TUMOR",
                    "decided_label_display": "Tumor Label",
                    "reason_codes": ["strong_consensus"],
                    "evidence_stats": {
                        "support_margin": 0.25,
                        "has_conflict": False,
                        "has_weak_support": False,
                        "n_supporting_references": 3,
                        "n_conflicting_references": 0
                    },
                    "artifact_refs": {
                        "consensus_decisions_json_path": "d.json",
                        "evidence_profiles_json_path": "e.json",
                        "report_summary_md_path": "s.md"
                    },
                    "top_supporting_reference_refs": [
                        {"reference_dataset_id": "DS1"}
                    ]
                },
                {
                    "comparison_id": "C2",
                    "decision_status": "no_consensus",
                    "decided_label_key": None,
                    "reason_codes": ["top_rank_conflict"],
                    "evidence_stats": {
                        "support_margin": 0.01,
                        "has_conflict": True,
                        "has_weak_support": True,
                        "n_supporting_references": 1,
                        "n_conflicting_references": 1
                    },
                    "artifact_refs": {},
                    "top_conflicting_reference_refs": [
                        {"reference_dataset_id": "DS3"}
                    ]
                }
            ]
        }
    }
    
    mock_paths = MagicMock(spec=ConsensusBundlePaths)
    mock_contract = MagicMock(spec=ConsensusBundleContractInfo)
    
    import_ctx = ConsensusBundleImportContext(
        manifest={},
        handoff_contract=handoff,
        paths=mock_paths,
        contract_info=mock_contract
    )
    
    session = build_comparator_review_session_context(import_ctx)
    
    assert session.source_consensus_run_id == "run123"
    assert len(session.rows) == 2
    
    # Check Row 0 (C1)
    r1 = session.rows[0]
    assert r1.comparison_id == "C1"
    assert r1.decision_status == "consensus"
    assert r1.support_margin == 0.25
    assert r1.has_conflict is False
    assert r1.reason_codes == ("strong_consensus",)
    assert r1.top_supporting_ref_ids == ("DS1",)
    assert r1.decision_artifact_path == "d.json"
    assert "c1" in r1.search_text
    
    # Check Row 1 (C2)
    r2 = session.rows[1]
    assert r2.comparison_id == "C2"
    assert r2.decision_status == "no_consensus"
    assert r2.has_conflict is True
    assert r2.has_weak_support is True
    assert r2.top_conflicting_ref_ids == ("DS3",)
    
    # Check Summary
    assert session.summary.n_total_rows == 2
    assert session.summary.n_consensus == 1
    assert session.summary.n_no_consensus == 1
    assert session.summary.n_with_conflict == 1
    assert session.summary.n_with_weak_support == 1

def test_build_review_session_deterministic_order():
    """
    Ensure rows follow the included_comparison_ids order.
    Corresponds to spec 6-5.
    """
    handoff = {
        "included_comparison_ids": ["Z1", "A1"],
        "decision_support": {
            "decision_evidence_refs": [
                {"comparison_id": "A1", "decision_status": "consensus"},
                {"comparison_id": "Z1", "decision_status": "consensus"}
            ]
        }
    }
    import_ctx = ConsensusBundleImportContext(
        manifest={}, handoff_contract=handoff, paths=MagicMock(), contract_info=MagicMock()
    )
    
    session = build_comparator_review_session_context(import_ctx)
    assert session.rows[0].comparison_id == "Z1"
    assert session.rows[1].comparison_id == "A1"

def test_build_review_session_missing_comparison_handling():
    """
    Ensure missing comparisons in decision_support block are captured as issues.
    Corresponds to spec 6-4.
    """
    handoff = {
        "included_comparison_ids": ["C1", "MISSING"],
        "decision_support": {
            "decision_evidence_refs": [
                {"comparison_id": "C1", "decision_status": "consensus"}
            ]
        }
    }
    import_ctx = ConsensusBundleImportContext(
        manifest={}, handoff_contract=handoff, paths=MagicMock(), contract_info=MagicMock()
    )
    
    session = build_comparator_review_session_context(import_ctx)
    assert len(session.rows) == 1
    assert session.rows[0].comparison_id == "C1"
    assert any("MISSING" in issue for issue in session.issues)
