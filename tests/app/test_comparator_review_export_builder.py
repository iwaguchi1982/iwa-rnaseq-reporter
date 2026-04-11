import os
import tempfile
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from iwa_rnaseq_reporter.app.comparator_consensus_import import ConsensusBundleImportContext, ConsensusBundlePaths
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewSessionContext, 
    ComparatorReviewRowSpec
)
from iwa_rnaseq_reporter.app.comparator_review_annotation import (
    ComparatorReviewAnnotationStore, 
    ComparatorReviewAnnotationSpec, 
    ComparatorReviewAnnotationSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_review_export_builder import (
    build_comparator_review_export_bundle,
    build_comparator_review_run_id
)
from iwa_rnaseq_reporter.app.comparator_review_import_builder import read_review_bundle

@pytest.fixture
def mock_contexts():
    # 1. Import Context (Source)
    # ConsensusBundleImportContext uses raw dict for manifest
    manifest = {"source_bundle_filename": "source.zip", "provenance": {"project": "test"}}
    paths = ConsensusBundlePaths(
        manifest_path=Path("m.json"), 
        bundle_root=Path("."),
        handoff_contract_path=Path("h.json"),
        decisions_json_path=Path("d.json"),
        evidence_profiles_path=Path("e.json")
    )
    import_ctx = MagicMock(spec=ConsensusBundleImportContext)
    import_ctx.manifest = manifest
    import_ctx.paths = paths
    
    # 2. Session Context
    row1 = ComparatorReviewRowSpec(
        comparison_id="comp1", 
        decision_status="consensus",
        decided_label_key="A",
        decided_label_display="Label A",
        support_margin=0.8,
        has_conflict=False,
        has_weak_support=False,
        n_supporting_refs=3,
        n_conflicting_refs=0,
        reason_codes=("RC1",),
        summary_artifact_path="art1.json"
    )
    session_ctx = MagicMock(spec=ComparatorReviewSessionContext)
    session_ctx.source_consensus_run_id = "run123"
    session_ctx.rows = (row1,)
    
    # 3. Annotation Store
    ann1 = ComparatorReviewAnnotationSpec(
        comparison_id="comp1",
        triage_status="reviewed",
        priority="high",
        review_note="Manual confirm",
        follow_up_required=False
    )
    summary = ComparatorReviewAnnotationSummarySpec(
        n_total_rows=1, n_annotated_rows=1, n_unreviewed=0, n_flagged=0,
        n_reviewed=1, n_handoff_candidate=0, n_high_priority=1, n_follow_up_required=0
    )
    ann_store = ComparatorReviewAnnotationStore(
        source_consensus_run_id="run123",
        annotations={"comp1": ann1},
        summary=summary
    )
    
    return import_ctx, session_ctx, ann_store

def test_export_import_roundtrip(mock_contexts):
    import_ctx, session_ctx, ann_store = mock_contexts
    
    # 1. Export to ZIP bytes
    bundle_bytes = build_comparator_review_export_bundle(import_ctx, session_ctx, ann_store)
    assert len(bundle_bytes) > 0
    
    # 2. Write to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf.write(bundle_bytes)
        tf_path = tf.name
        
    try:
        # 3. Import from ZIP
        imp_ctx = read_review_bundle(tf_path)
        
        # 4. Verify
        assert imp_ctx.is_valid
        assert imp_ctx.manifest.source_consensus_run_id == "run123"
        assert imp_ctx.summary.n_reviewed == 1
        assert imp_ctx.summary.n_high_priority == 1
        
        # Verify Rows
        assert len(imp_ctx.review_rows) == 1
        row = imp_ctx.review_rows[0]
        assert row.comparison_id == "comp1"
        assert row.triage_status == "reviewed"
        assert row.priority == "high"
        assert row.review_note == "Manual confirm"
        
        # Verify Handoff
        assert imp_ctx.handoff_contract.source_consensus_run_id == "run123"
        assert imp_ctx.handoff_contract.review_decision_refs[0].triage_status == "reviewed"
        
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)

def test_export_unreviewed_row(mock_contexts):
    import_ctx, session_ctx, ann_store = mock_contexts
    
    # Empty annotations
    empty_ann_store = ComparatorReviewAnnotationStore(
        source_consensus_run_id="run123",
        annotations={},
        summary=None
    )
    
    bundle_bytes = build_comparator_review_export_bundle(import_ctx, session_ctx, empty_ann_store)
    
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf.write(bundle_bytes)
        tf_path = tf.name
        
    try:
        imp_ctx = read_review_bundle(tf_path)
        assert imp_ctx.is_valid
        assert len(imp_ctx.review_rows) == 1
        assert imp_ctx.review_rows[0].triage_status == "unreviewed"
        assert imp_ctx.summary.n_unreviewed == 1
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
