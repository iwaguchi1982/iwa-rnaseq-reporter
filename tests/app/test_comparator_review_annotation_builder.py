import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_review_session import ComparatorReviewSessionContext, ComparatorReviewRowSpec
from iwa_rnaseq_reporter.app.comparator_review_annotation import ComparatorReviewAnnotationSpec
from iwa_rnaseq_reporter.app.comparator_review_annotation_builder import (
    build_empty_comparator_review_annotation_store,
    upsert_comparator_review_annotation,
    remove_comparator_review_annotation,
    get_comparator_review_annotation
)

@pytest.fixture
def mock_session():
    row1 = ComparatorReviewRowSpec(comparison_id="comp1", decision_status="consensus")
    row2 = ComparatorReviewRowSpec(comparison_id="comp2", decision_status="no_consensus")
    
    session = MagicMock(spec=ComparatorReviewSessionContext)
    session.source_consensus_run_id = "run_123"
    session.rows = (row1, row2)
    return session

def test_annotation_store_lifecycle(mock_session):
    # 1. Initialize
    store = build_empty_comparator_review_annotation_store(mock_session)
    assert store.source_consensus_run_id == "run_123"
    assert store.summary.n_total_rows == 2
    assert store.summary.n_unreviewed == 2
    assert store.summary.n_annotated_rows == 0

    # 2. Upsert (Reviewed)
    ann1 = ComparatorReviewAnnotationSpec(
        comparison_id="comp1",
        triage_status="reviewed",
        priority="normal",
        review_note="Looks good"
    )
    store = upsert_comparator_review_annotation(store, mock_session, ann1)
    
    assert store.summary.n_annotated_rows == 1
    assert store.summary.n_reviewed == 1
    assert store.summary.n_unreviewed == 1
    assert get_comparator_review_annotation(store, "comp1").review_note == "Looks good"

    # 3. Upsert (Flagged High Priority)
    ann2 = ComparatorReviewAnnotationSpec(
        comparison_id="comp2",
        triage_status="flagged",
        priority="high",
        follow_up_required=True
    )
    store = upsert_comparator_review_annotation(store, mock_session, ann2)
    
    assert store.summary.n_annotated_rows == 2
    assert store.summary.n_flagged == 1
    assert store.summary.n_high_priority == 1
    assert store.summary.n_follow_up_required == 1
    assert store.summary.n_unreviewed == 0

    # 4. Remove
    store = remove_comparator_review_annotation(store, mock_session, "comp1")
    assert store.summary.n_annotated_rows == 1
    assert store.summary.n_reviewed == 0
    assert store.summary.n_unreviewed == 1

def test_upsert_mismatch_guards(mock_session):
    store = build_empty_comparator_review_annotation_store(mock_session)
    
    # Run ID mismatch
    other_session = MagicMock(spec=ComparatorReviewSessionContext)
    other_session.source_consensus_run_id = "run_999"
    
    ann = ComparatorReviewAnnotationSpec(comparison_id="comp1", triage_status="reviewed", priority="normal")
    with pytest.raises(ValueError, match="Store session mismatch"):
        upsert_comparator_review_annotation(store, other_session, ann)
        
    # Invalid comparison ID
    ann_invalid = ComparatorReviewAnnotationSpec(comparison_id="invalid_id", triage_status="reviewed", priority="normal")
    with pytest.raises(ValueError, match="not found in active session"):
        upsert_comparator_review_annotation(store, mock_session, ann_invalid)
