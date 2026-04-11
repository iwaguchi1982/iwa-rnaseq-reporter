import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_consensus_import import ConsensusBundleImportContext
from iwa_rnaseq_reporter.app.comparator_review_session import ComparatorReviewSessionContext, ComparatorReviewRowSpec
from iwa_rnaseq_reporter.app.comparator_review_drilldown_builder import build_comparator_review_drilldown_context

def test_build_drilldown_context_success():
    # Setup mock row
    mock_row = ComparatorReviewRowSpec(
        comparison_id="comp_1",
        decision_status="consensus",
        decided_label_key="A",
        decided_label_display="Label A"
    )
    
    # Setup mock session context
    mock_session = MagicMock(spec=ComparatorReviewSessionContext)
    mock_session.rows = (mock_row,)
    
    # Setup mock import context with handoff
    handoff = {
        "decision_support": {
            "decision_evidence_refs": [
                {
                    "comparison_id": "comp_1",
                    "decision_status": "consensus",
                    "decided_label_key": "A",
                    "decided_label_display": "Label A",
                    "evidence_stats": {"support_margin": 0.8},
                    "top_supporting_reference_refs": [
                        {"reference_dataset_id": "ds1", "integrated_score": 0.9, "rank": 1}
                    ],
                    "artifact_refs": {"report_summary_md_path": "path/to/summary.md"}
                }
            ]
        }
    }
    
    mock_import = MagicMock(spec=ConsensusBundleImportContext)
    mock_import.handoff_contract = handoff
    mock_import.decisions_json = {"comp_1": {"raw": "decision"}}
    mock_import.evidence_profiles_json = [{"comparison_id": "comp_1", "raw": "profile"}]
    
    # Execute
    ctx = build_comparator_review_drilldown_context(mock_import, mock_session, "comp_1")
    
    # Assertions
    assert ctx.selected_comparison_id == "comp_1"
    assert ctx.row.comparison_id == "comp_1"
    assert ctx.decision_detail.support_margin == 0.8
    assert len(ctx.decision_detail.top_supporting_refs) == 1
    assert ctx.decision_detail.top_supporting_refs[0].reference_dataset_id == "ds1"
    assert ctx.decision_detail.artifacts.report_summary_md_path == "path/to/summary.md"
    assert ctx.json_inspection.decision_json == {"raw": "decision"}
    assert ctx.json_inspection.evidence_profile_json == {"comparison_id": "comp_1", "raw": "profile"}

def test_build_drilldown_context_not_found():
    mock_session = MagicMock(spec=ComparatorReviewSessionContext)
    mock_session.rows = ()
    mock_import = MagicMock(spec=ConsensusBundleImportContext)
    
    with pytest.raises(ValueError, match="not found in active review session"):
        build_comparator_review_drilldown_context(mock_import, mock_session, "missing")

def test_build_drilldown_context_missing_handoff_ref():
    mock_row = ComparatorReviewRowSpec(comparison_id="comp_1", decision_status="ok")
    mock_session = MagicMock(spec=ComparatorReviewSessionContext)
    mock_session.rows = (mock_row,)
    
    mock_import = MagicMock(spec=ConsensusBundleImportContext)
    mock_import.handoff_contract = {"decision_support": {"decision_evidence_refs": []}}
    
    with pytest.raises(ValueError, match="missing in handoff contract"):
        build_comparator_review_drilldown_context(mock_import, mock_session, "comp_1")
