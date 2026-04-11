from typing import Optional, Dict
from .comparator_review_session import ComparatorReviewSessionContext
from .comparator_review_annotation import (
    ComparatorReviewAnnotationSpec,
    ComparatorReviewAnnotationSummarySpec,
    ComparatorReviewAnnotationStore
)

def build_empty_comparator_review_annotation_store(
    session_ctx: ComparatorReviewSessionContext
) -> ComparatorReviewAnnotationStore:
    """Initialize an empty annotation store for a new session."""
    store = ComparatorReviewAnnotationStore(
        source_consensus_run_id=session_ctx.source_consensus_run_id,
        annotations={}
    )
    # Calculate initial summary
    summary = build_comparator_review_annotation_summary(store, session_ctx)
    return ComparatorReviewAnnotationStore(
        source_consensus_run_id=store.source_consensus_run_id,
        annotations=store.annotations,
        summary=summary
    )

def get_comparator_review_annotation(
    store: ComparatorReviewAnnotationStore,
    comparison_id: str
) -> Optional[ComparatorReviewAnnotationSpec]:
    """Retrieve annotation for a specific comparison if it exists."""
    return store.annotations.get(comparison_id)

def build_comparator_review_annotation_summary(
    store: ComparatorReviewAnnotationStore,
    session_ctx: ComparatorReviewSessionContext
) -> ComparatorReviewAnnotationSummarySpec:
    """Calculate aggregated review progress metrics."""
    n_total = len(session_ctx.rows)
    ann_dict = store.annotations
    n_annotated = len(ann_dict)
    
    counts = {
        "flagged": 0,
        "reviewed": 0,
        "handoff_candidate": 0,
        "unreviewed": 0
    }
    n_high = 0
    n_follow_up = 0
    
    # Active annotations
    for ann in ann_dict.values():
        st = ann.triage_status
        if st in counts:
            counts[st] += 1
        if ann.priority == "high":
            n_high += 1
        if ann.follow_up_required:
            n_follow_up += 1
            
    # "Unreviewed" includes comparisons without any annotation entry
    # n_unreviewed = n_total - (flagged + reviewed + handoff_candidate)
    # But for clarity based on explicit status:
    # Actually, any row NOT in ann_dict is implicitly "unreviewed".
    # And any row IN ann_dict with triage_status=="unreviewed" is also "unreviewed".
    
    # Calculate implicit unreviewed
    annotated_ids = set(ann_dict.keys())
    implicit_unreviewed = 0
    for row in session_ctx.rows:
        if row.comparison_id not in annotated_ids:
            implicit_unreviewed += 1
            
    total_unreviewed = counts["unreviewed"] + implicit_unreviewed

    return ComparatorReviewAnnotationSummarySpec(
        n_total_rows=n_total,
        n_annotated_rows=n_annotated,
        n_unreviewed=total_unreviewed,
        n_flagged=counts["flagged"],
        n_reviewed=counts["reviewed"],
        n_handoff_candidate=counts["handoff_candidate"],
        n_high_priority=n_high,
        n_follow_up_required=n_follow_up
    )

def upsert_comparator_review_annotation(
    store: ComparatorReviewAnnotationStore,
    session_ctx: ComparatorReviewSessionContext,
    annotation: ComparatorReviewAnnotationSpec
) -> ComparatorReviewAnnotationStore:
    """Add or update an annotation. Returns a new store instance."""
    # Safety Check: Session Mismatch
    if store.source_consensus_run_id != session_ctx.source_consensus_run_id:
        raise ValueError("Store session mismatch: Annotation belongs to a different consensus run.")
        
    # Safety Check: Valid Comparison
    valid_ids = {r.comparison_id for r in session_ctx.rows}
    if annotation.comparison_id not in valid_ids:
        raise ValueError(f"Comparison ID '{annotation.comparison_id}' not found in active session.")
        
    new_annotations = dict(store.annotations)
    new_annotations[annotation.comparison_id] = annotation
    
    new_store_pre = ComparatorReviewAnnotationStore(
        source_consensus_run_id=store.source_consensus_run_id,
        annotations=new_annotations
    )
    summary = build_comparator_review_annotation_summary(new_store_pre, session_ctx)
    
    return ComparatorReviewAnnotationStore(
        source_consensus_run_id=store.source_consensus_run_id,
        annotations=new_annotations,
        summary=summary
    )

def remove_comparator_review_annotation(
    store: ComparatorReviewAnnotationStore,
    session_ctx: ComparatorReviewSessionContext,
    comparison_id: str
) -> ComparatorReviewAnnotationStore:
    """Remove an annotation. Returns a new store instance."""
    if comparison_id not in store.annotations:
        return store
        
    new_annotations = dict(store.annotations)
    del new_annotations[comparison_id]
    
    new_store_pre = ComparatorReviewAnnotationStore(
        source_consensus_run_id=store.source_consensus_run_id,
        annotations=new_annotations
    )
    summary = build_comparator_review_annotation_summary(new_store_pre, session_ctx)
    
    return ComparatorReviewAnnotationStore(
        source_consensus_run_id=store.source_consensus_run_id,
        annotations=new_annotations,
        summary=summary
    )
