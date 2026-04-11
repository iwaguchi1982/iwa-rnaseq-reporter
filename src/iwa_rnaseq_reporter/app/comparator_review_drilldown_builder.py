from typing import Optional, Dict, Any, List, Union, Tuple
from .comparator_consensus_import import ConsensusBundleImportContext
from .comparator_review_session import ComparatorReviewSessionContext, ComparatorReviewRowSpec
from .comparator_review_drilldown import (
    ComparatorReviewDrilldownContext,
    ComparatorReviewDecisionDetailSpec,
    ComparatorReviewReferenceDetailSpec,
    ComparatorReviewArtifactDetailSpec,
    ComparatorReviewJsonInspectionSpec
)

def _lookup_row(session_ctx: ComparatorReviewSessionContext, comparison_id: str) -> Optional[ComparatorReviewRowSpec]:
    for row in session_ctx.rows:
        if row.comparison_id == comparison_id:
            return row
    return None

def _lookup_evidence_ref(import_ctx: ConsensusBundleImportContext, comparison_id: str) -> Optional[Dict[str, Any]]:
    handoff = import_ctx.handoff_contract
    if not handoff:
        return None
    ds = handoff.get("decision_support", {})
    refs = ds.get("decision_evidence_refs", [])
    for ref in refs:
        if ref.get("comparison_id") == comparison_id:
            return ref
    return None

def _lookup_json_by_id(data: Optional[Union[Dict[str, Any], Tuple[Dict[str, Any], ...], List[Dict[str, Any]]]], comparison_id: str) -> Optional[Dict[str, Any]]:
    """Defensive lookup for raw JSON payloads which might be a dict or list/tuple."""
    if not data:
        return None
    
    # CASE 1: Data is a dict where keys are comparison_ids
    if isinstance(data, dict):
        if comparison_id in data:
            return data[comparison_id]
        # Sometimes keys are numeric or nested, but standard repo pattern is comparison_id as key
        return None
        
    # CASE 2: Data is a sequence of dicts
    if isinstance(data, (list, tuple)):
        for item in data:
            if isinstance(item, dict) and item.get("comparison_id") == comparison_id:
                return item
    
    return None

def _build_reference_detail(ref_raw: Dict[str, Any]) -> ComparatorReviewReferenceDetailSpec:
    return ComparatorReviewReferenceDetailSpec(
        reference_dataset_id=ref_raw.get("reference_dataset_id", "unknown"),
        reference_comparison_id=ref_raw.get("reference_comparison_id", "unknown"),
        label_key=ref_raw.get("label_key"),
        label_display=ref_raw.get("label_display"),
        integrated_score=ref_raw.get("integrated_score"),
        rank=ref_raw.get("rank")
    )

def build_comparator_review_drilldown_context(
    import_ctx: ConsensusBundleImportContext,
    session_ctx: ComparatorReviewSessionContext,
    selected_comparison_id: str
) -> ComparatorReviewDrilldownContext:
    """
    Construct a complete drilldown context for the selected comparison.
    Orchestrates lookup of formal metrics, artifact pointers, and raw JSON payloads.
    """
    row = _lookup_row(session_ctx, selected_comparison_id)
    if not row:
        raise ValueError(f"Comparison ID '{selected_comparison_id}' not found in active review session.")
    
    ev_ref = _lookup_evidence_ref(import_ctx, selected_comparison_id)
    if not ev_ref:
        # In v0.20.3, it's a blocker if handoff detail is missing while row exists
        raise ValueError(f"Detail evidence for '{selected_comparison_id}' missing in handoff contract.")

    # 1. Decision Details
    stats = ev_ref.get("evidence_stats", {})
    art_refs = ev_ref.get("artifact_refs", {})
    
    sup_refs = tuple(_build_reference_detail(r) for r in ev_ref.get("top_supporting_reference_refs", []))
    con_refs = tuple(_build_reference_detail(r) for r in ev_ref.get("top_conflicting_reference_refs", []))
    
    artifacts = ComparatorReviewArtifactDetailSpec(
        consensus_manifest_path=art_refs.get("consensus_manifest_path"),
        consensus_handoff_contract_path=art_refs.get("consensus_handoff_contract_path"),
        consensus_decisions_json_path=art_refs.get("consensus_decisions_json_path"),
        evidence_profiles_json_path=art_refs.get("evidence_profiles_json_path"),
        consensus_decisions_csv_path=art_refs.get("consensus_decisions_csv_path"),
        report_summary_md_path=art_refs.get("report_summary_md_path")
    )
    
    decision_detail = ComparatorReviewDecisionDetailSpec(
        comparison_id=selected_comparison_id,
        decision_status=ev_ref.get("decision_status", "unknown"),
        decided_label_key=ev_ref.get("decided_label_key"),
        decided_label_display=ev_ref.get("decided_label_display"),
        support_margin=stats.get("support_margin"),
        has_conflict=stats.get("has_conflict", False),
        has_weak_support=stats.get("has_weak_support", False),
        n_supporting_refs=stats.get("n_supporting_references", 0),
        n_conflicting_refs=stats.get("n_conflicting_references", 0),
        n_competing_candidates=stats.get("n_competing_candidates"),
        reason_codes=tuple(ev_ref.get("reason_codes", [])),
        top_supporting_refs=sup_refs,
        top_conflicting_refs=con_refs,
        artifacts=artifacts
    )
    
    # 2. Raw JSON Inspection
    json_inspection = ComparatorReviewJsonInspectionSpec(
        decision_json=_lookup_json_by_id(import_ctx.decisions_json, selected_comparison_id),
        evidence_profile_json=_lookup_json_by_id(import_ctx.evidence_profiles_json, selected_comparison_id)
    )
    
    issues: List[str] = []
    if not json_inspection.decision_json:
        issues.append("Decision JSON payload missing for this comparison")
    if not json_inspection.evidence_profile_json:
        issues.append("Evidence Profile JSON payload missing for this comparison")

    return ComparatorReviewDrilldownContext(
        selected_comparison_id=selected_comparison_id,
        row=row,
        decision_detail=decision_detail,
        json_inspection=json_inspection,
        issues=tuple(issues)
    )
