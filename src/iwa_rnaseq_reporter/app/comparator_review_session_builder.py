from typing import Tuple, Dict, Any, List, Optional
from iwa_rnaseq_reporter.app.comparator_consensus_import import ConsensusBundleImportContext
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewRowSpec,
    ComparatorReviewSessionSummarySpec,
    ComparatorReviewSessionContext
)

def _build_search_text(row: ComparatorReviewRowSpec) -> str:
    """
    Construct a simple deterministic search index for the row.
    """
    parts = [
        row.comparison_id,
        row.decision_status,
        row.decided_label_key or "",
        row.decided_label_display or "",
        ",".join(row.reason_codes)
    ]
    return " ".join(p for p in parts if p).lower()

def build_comparator_review_row(
    ev_ref: Dict[str, Any],
    handoff: Dict[str, Any]
) -> ComparatorReviewRowSpec:
    """
    Transform a decision evidence ref into a flattened review row.
    Source of truth: handoff.decision_support.decision_evidence_refs[i]
    """
    comp_id = ev_ref.get("comparison_id")
    stats = ev_ref.get("evidence_stats", {})
    art_refs = ev_ref.get("artifact_refs", {})
    
    # Extract top refs IDs for quick lookup
    top_sup = ev_ref.get("top_supporting_reference_refs", [])
    top_sup_ids = tuple(r.get("reference_dataset_id", "unknown") for r in top_sup)
    
    top_con = ev_ref.get("top_conflicting_reference_refs", [])
    top_con_ids = tuple(r.get("reference_dataset_id", "unknown") for r in top_con)

    row = ComparatorReviewRowSpec(
        comparison_id=comp_id,
        decision_status=ev_ref.get("decision_status", "unknown"),
        decided_label_key=ev_ref.get("decided_label_key"),
        decided_label_display=ev_ref.get("decided_label_display"),
        support_margin=stats.get("support_margin"),
        has_conflict=stats.get("has_conflict", False),
        has_weak_support=stats.get("has_weak_support", False),
        reason_codes=tuple(ev_ref.get("reason_codes", [])),
        n_supporting_refs=stats.get("n_supporting_references", 0),
        n_conflicting_refs=stats.get("n_conflicting_references", 0),
        top_supporting_ref_ids=top_sup_ids,
        top_conflicting_ref_ids=top_con_ids,
        decision_artifact_path=art_refs.get("consensus_decisions_json_path"),
        evidence_artifact_path=art_refs.get("evidence_profiles_json_path"),
        summary_artifact_path=art_refs.get("report_summary_md_path")
    )
    
    # Post-process search text
    # Note: We can't mutate frozen dataclass directly, so we'd need to add it 
    # to the constructor if we want it in the final product.
    # For v0.20.1, we'll recreate the object with search_text if needed, 
    # or just include it in the initial build.
    
    final_row = ComparatorReviewRowSpec(
        **{k: getattr(row, k) for k in row.__dataclass_fields__ if k != "search_text"},
        search_text=_build_search_text(row)
    )
    return final_row

def build_review_session_summary(
    rows: Tuple[ComparatorReviewRowSpec, ...]
) -> ComparatorReviewSessionSummarySpec:
    """
    Aggregate metrics from the list of review rows.
    """
    n_total = len(rows)
    counts = {
        "consensus": 0,
        "no_consensus": 0,
        "insufficient_evidence": 0,
        "abstain": 0
    }
    n_conflict = 0
    n_weak = 0
    n_no_label = 0
    
    for r in rows:
        st = r.decision_status
        if st in counts:
            counts[st] += 1
        
        if r.has_conflict:
            n_conflict += 1
        if r.has_weak_support:
            n_weak += 1
        if not r.decided_label_key:
            n_no_label += 1
            
    return ComparatorReviewSessionSummarySpec(
        n_total_rows=n_total,
        n_consensus=counts["consensus"],
        n_no_consensus=counts["no_consensus"],
        n_insufficient_evidence=counts["insufficient_evidence"],
        n_with_conflict=n_conflict,
        n_with_weak_support=n_weak,
        n_without_decided_label=n_no_label,
        decision_status_counts=counts
    )

def _validate_unique_ids(ids: List[str], label: str):
    """
    Ensure all IDs in the list are unique. Raises ValueError on duplicate.
    """
    seen = set()
    for comp_id in ids:
        if comp_id in seen:
            raise ValueError(f"Duplicate comparison_id detected in {label}: '{comp_id}'")
        seen.add(comp_id)

def build_comparator_review_session_context(
    import_ctx: ConsensusBundleImportContext
) -> ComparatorReviewSessionContext:
    """
    Transform a loaded consensus bundle into a review session context.
    Orchestrates row building and summary generation.
    """
    handoff = import_ctx.handoff_contract
    if not handoff:
        raise ValueError("Cannot build review session without handoff contract")
        
    ds = handoff.get("decision_support")
    if not ds:
        raise ValueError("Missing 'decision_support' block in handoff contract")
        
    ds_refs = ds.get("decision_evidence_refs", [])
    
    # v0.20.1a Hardening: Validate uniqueness to prevent silent drop
    included_ids = handoff.get("included_comparison_ids", [])
    if included_ids:
        _validate_unique_ids(included_ids, "included_comparison_ids")
        
    evidence_ids = [r.get("comparison_id") for r in ds_refs if r.get("comparison_id")]
    _validate_unique_ids(evidence_ids, "decision_support.decision_evidence_refs")

    # v0.20.1 Ordering: Follow handoff included_comparison_ids if available (Deterministic)
    # The decision_evidence_refs are usually already in sync, but we ensure robustness.
    ref_map = {r.get("comparison_id"): r for r in ds_refs if r.get("comparison_id")}
    
    if not included_ids:
        # Fallback to current refs order
        included_ids = evidence_ids
    
    rows: List[ComparatorReviewRowSpec] = []
    issues: List[str] = []
    
    for comp_id in included_ids:
        ev_ref = ref_map.get(comp_id)
        if not ev_ref:
            issues.append(f"Comparison '{comp_id}' missing in decision_support block")
            continue
            
        rows.append(build_comparator_review_row(ev_ref, handoff))
        
    rows_tuple = tuple(rows)
    summary = build_review_session_summary(rows_tuple)
    
    return ComparatorReviewSessionContext(
        source_consensus_run_id=handoff.get("consensus_run_id", "unknown"),
        rows=rows_tuple,
        summary=summary,
        issues=tuple(issues),
        included_comparison_ids=tuple(included_ids),
        decided_label_keys=tuple(handoff.get("decided_label_keys", []))
    )

def build_comparator_review_session_context_from_bundle(
    manifest_path: Any
) -> ComparatorReviewSessionContext:
    """
    High-level convenience function to load a bundle and create a review session in one go.
    """
    from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import read_consensus_bundle
    
    import_ctx = read_consensus_bundle(manifest_path)
    return build_comparator_review_session_context(import_ctx)
