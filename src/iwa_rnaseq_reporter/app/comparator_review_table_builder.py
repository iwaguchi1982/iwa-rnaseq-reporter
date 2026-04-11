import pandas as pd
from typing import Tuple, List, Dict
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewRowSpec,
    ComparatorReviewSessionContext
)
from iwa_rnaseq_reporter.app.comparator_review_table import (
    ComparatorReviewFilterSpec,
    ComparatorReviewTableSummarySpec,
    ComparatorReviewTableContext
)

def _matches_decision_status(row: ComparatorReviewRowSpec, statuses: Tuple[str, ...]) -> bool:
    if not statuses:
        return True
    return row.decision_status in statuses

def _matches_decided_label(row: ComparatorReviewRowSpec, label_keys: Tuple[str, ...]) -> bool:
    if not label_keys:
        return True
    # If key is None, it won't match any specified keys (which reflect present labels)
    return row.decided_label_key in label_keys

def _matches_conflict_mode(row: ComparatorReviewRowSpec, mode: str) -> bool:
    if mode == "all":
        return True
    if mode == "conflict_only":
        return row.has_conflict is True
    if mode == "no_conflict_only":
        return row.has_conflict is False
    return True

def _matches_weak_support_mode(row: ComparatorReviewRowSpec, mode: str) -> bool:
    if mode == "all":
        return True
    if mode == "weak_only":
        return row.has_weak_support is True
    if mode == "not_weak_only":
        return row.has_weak_support is False
    return True

def _matches_search_query(row: ComparatorReviewRowSpec, query: str) -> bool:
    if not query or not query.strip():
        return True
    return query.lower() in row.search_text.lower()

def _build_filtered_summary(
    all_rows: Tuple[ComparatorReviewRowSpec, ...],
    filtered_rows: Tuple[ComparatorReviewRowSpec, ...]
) -> ComparatorReviewTableSummarySpec:
    """
    Aggregate metrics from the filtered subset of rows.
    """
    counts = {
        "consensus": 0,
        "no_consensus": 0,
        "insufficient_evidence": 0,
        "abstain": 0
    }
    label_counts: Dict[str, int] = {}
    n_conflict = 0
    n_weak = 0
    
    for r in filtered_rows:
        st = r.decision_status
        if st in counts:
            counts[st] += 1
            
        if r.decided_label_key:
            lk = r.decided_label_key
            label_counts[lk] = label_counts.get(lk, 0) + 1
            
        if r.has_conflict:
            n_conflict += 1
        if r.has_weak_support:
            n_weak += 1
            
    return ComparatorReviewTableSummarySpec(
        n_total_rows=len(all_rows),
        n_filtered_rows=len(filtered_rows),
        n_consensus=counts["consensus"],
        n_no_consensus=counts["no_consensus"],
        n_insufficient_evidence=counts["insufficient_evidence"],
        n_with_conflict=n_conflict,
        n_with_weak_support=n_weak,
        decision_status_counts=counts,
        decided_label_counts=label_counts
    )

def build_comparator_review_table_context(
    session_ctx: ComparatorReviewSessionContext,
    filters: ComparatorReviewFilterSpec
) -> ComparatorReviewTableContext:
    """
    Apply filters to review session rows and generate a table context.
    Corresponds to spec 115-208.
    """
    filtered: List[ComparatorReviewRowSpec] = []
    
    for row in session_ctx.rows:
        if not _matches_decision_status(row, filters.decision_statuses):
            continue
        if not _matches_decided_label(row, filters.decided_label_keys):
            continue
        if not _matches_conflict_mode(row, filters.conflict_mode):
            continue
        if not _matches_weak_support_mode(row, filters.weak_support_mode):
            continue
        if not _matches_search_query(row, filters.search_query):
            continue
            
        filtered.append(row)
        
    filtered_tuple = tuple(filtered)
    summary = _build_filtered_summary(session_ctx.rows, filtered_tuple)
    
    return ComparatorReviewTableContext(
        source_session=session_ctx,
        filters=filters,
        filtered_rows=filtered_tuple,
        summary=summary
    )

def build_comparator_review_table_dataframe(
    rows: Tuple[ComparatorReviewRowSpec, ...]
) -> pd.DataFrame:
    """
    Transform rows into a display-oriented DataFrame.
    Corresponds to spec 210-242.
    """
    if not rows:
        return pd.DataFrame()
        
    data = []
    for r in rows:
        # Label fallback logic (spec 225-229)
        label = r.decided_label_display or r.decided_label_key or "-"
        
        # Margin formatting (spec 230-232)
        margin = r.support_margin if r.support_margin is not None else "-"
        
        data.append({
            "comparison_id": r.comparison_id,
            "decision_status": r.decision_status,
            "decided_label": label,
            "support_margin": margin,
            "has_conflict": "yes" if r.has_conflict else "no",
            "has_weak_support": "yes" if r.has_weak_support else "no",
            "n_supporting_refs": r.n_supporting_refs,
            "n_conflicting_refs": r.n_conflicting_refs,
            "reason_codes": ", ".join(r.reason_codes)
        })
        
    return pd.DataFrame(data)
