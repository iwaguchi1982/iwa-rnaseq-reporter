import io
import json
import zipfile
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .comparator_review_session import ComparatorReviewSessionContext
from .comparator_review_annotation import ComparatorReviewAnnotationStore, ComparatorReviewAnnotationSpec
from .comparator_consensus_import import ConsensusBundleImportContext
from .comparator_review_export import (
    ComparatorReviewExportManifestSpec,
    ComparatorReviewExportRowSpec,
    ComparatorReviewSummarySpec,
    ComparatorReviewExportPayload
)
from .comparator_review_handoff import (
    ComparatorReviewBundleRefSpec,
    ComparatorReviewSourceRefSpec,
    ComparatorReviewDecisionRefSpec,
    ComparatorReviewHandoffPayload
)

def build_comparator_review_run_id(source_consensus_run_id: str) -> str:
    """Generate a unique ID for the review run."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"review-{source_consensus_run_id}-{ts}"

def build_comparator_review_bundle_filename(review_run_id: str) -> str:
    """Generate the ZIP filename for the review bundle."""
    return f"{review_run_id}.zip"

def build_comparator_review_export_payload(
    import_ctx: ConsensusBundleImportContext,
    session_ctx: ComparatorReviewSessionContext,
    annotation_store: ComparatorReviewAnnotationStore,
    review_run_id: str
) -> ComparatorReviewExportPayload:
    """Consolidate automated results and reviewer annotations into an export payload."""
    now_str = datetime.now().isoformat()
    
    # 1. Build Rows (Full Session)
    rows = []
    for s_row in session_ctx.rows:
        cid = s_row.comparison_id
        ann = annotation_store.annotations.get(cid)
        
        # Default annotation values if unreviewed
        t_status = ann.triage_status if ann else "unreviewed"
        priority = ann.priority if ann else "normal"
        f_up = ann.follow_up_required if ann else False
        note = ann.review_note if ann else ""
        
        row = ComparatorReviewExportRowSpec(
            comparison_id=cid,
            decision_status=s_row.decision_status,
            decided_label_key=s_row.decided_label_key,
            decided_label_display=s_row.decided_label_display,
            support_margin=s_row.support_margin,
            has_conflict=s_row.has_conflict,
            has_weak_support=s_row.has_weak_support,
            n_supporting_refs=s_row.n_supporting_refs,
            n_conflicting_refs=s_row.n_conflicting_refs,
            triage_status=t_status,
            priority=priority,
            follow_up_required=f_up,
            review_note=note,
            reason_codes=s_row.reason_codes,
            summary_artifact_path=s_row.summary_artifact_path
        )
        rows.append(row)
        
    # 2. Extract Status Counts
    d_status_counts = {}
    for r in rows:
        d_status_counts[r.decision_status] = d_status_counts.get(r.decision_status, 0) + 1
        
    t_status_counts = {}
    if annotation_store.summary:
        s = annotation_store.summary
        t_status_counts = {
            "unreviewed": s.n_unreviewed,
            "flagged": s.n_flagged,
            "reviewed": s.n_reviewed,
            "handoff_candidate": s.n_handoff_candidate
        }

    summary = ComparatorReviewSummarySpec(
        n_total_rows=len(rows),
        n_annotated_rows=len(annotation_store.annotations),
        n_unreviewed=annotation_store.summary.n_unreviewed if annotation_store.summary else len(rows),
        n_flagged=annotation_store.summary.n_flagged if annotation_store.summary else 0,
        n_reviewed=annotation_store.summary.n_reviewed if annotation_store.summary else 0,
        n_handoff_candidate=annotation_store.summary.n_handoff_candidate if annotation_store.summary else 0,
        n_high_priority=annotation_store.summary.n_high_priority if annotation_store.summary else 0,
        n_follow_up_required=annotation_store.summary.n_follow_up_required if annotation_store.summary else 0,
        decision_status_counts=d_status_counts,
        triage_status_counts=t_status_counts
    )
    
    # 3. Build Manifest
    manifest = ComparatorReviewExportManifestSpec(
        generated_at=now_str,
        provenance=import_ctx.manifest.get("provenance", {}) if import_ctx.manifest else {},
        review_run_id=review_run_id,
        source_consensus_run_id=session_ctx.source_consensus_run_id,
        n_total_rows=summary.n_total_rows,
        n_annotated_rows=summary.n_annotated_rows,
        n_unreviewed=summary.n_unreviewed,
        n_flagged=summary.n_flagged,
        n_reviewed=summary.n_reviewed,
        n_handoff_candidate=summary.n_handoff_candidate,
        n_high_priority=summary.n_high_priority,
        n_follow_up_required=summary.n_follow_up_required,
        source_bundle_filename=import_ctx.manifest.get("source_bundle_filename") if import_ctx.manifest else None
    )
    
    return ComparatorReviewExportPayload(
        manifest=manifest,
        review_rows=tuple(rows),
        summary=summary
    )

def build_comparator_review_handoff_payload(
    import_ctx: ConsensusBundleImportContext,
    session_ctx: ComparatorReviewSessionContext,
    annotation_store: ComparatorReviewAnnotationStore,
    export_payload: ComparatorReviewExportPayload,
    review_bundle_filename: str,
    review_run_id: str
) -> ComparatorReviewHandoffPayload:
    """Build the compact handoff contract for downstream integration."""
    
    # 1. Source Refs Snapshot
    s_refs = ComparatorReviewSourceRefSpec(
        source_consensus_run_id=session_ctx.source_consensus_run_id,
        source_bundle_filename=import_ctx.manifest.get("source_bundle_filename") if import_ctx.manifest else None,
        source_consensus_manifest_path=str(import_ctx.paths.manifest_path) if import_ctx.paths else None,
        source_consensus_handoff_contract_path=str(import_ctx.paths.handoff_contract_path) if import_ctx.paths and import_ctx.paths.handoff_contract_path else None,
        source_consensus_decisions_json_path=str(import_ctx.paths.decisions_json_path) if import_ctx.paths and import_ctx.paths.decisions_json_path else None,
        source_evidence_profiles_json_path=str(import_ctx.paths.evidence_profiles_path) if import_ctx.paths and import_ctx.paths.evidence_profiles_path else None
    )
    
    # 2. Bundle Refs (Relative)
    b_refs = ComparatorReviewBundleRefSpec(
        review_bundle_filename=review_bundle_filename
    )
    
    # 3. Decision Refs (Compact)
    d_refs = []
    for r in export_payload.review_rows:
        ref = ComparatorReviewDecisionRefSpec(
            comparison_id=r.comparison_id,
            decision_status=r.decision_status,
            decided_label_key=r.decided_label_key,
            decided_label_display=r.decided_label_display,
            triage_status=r.triage_status,
            priority=r.priority,
            follow_up_required=r.follow_up_required,
            review_note=r.review_note,
            has_conflict=r.has_conflict,
            has_weak_support=r.has_weak_support,
            support_margin=r.support_margin
        )
        d_refs.append(ref)
        
    return ComparatorReviewHandoffPayload(
        generated_at=export_payload.manifest.generated_at,
        provenance=export_payload.manifest.provenance,
        review_run_id=review_run_id,
        source_consensus_run_id=session_ctx.source_consensus_run_id,
        bundle_refs=b_refs,
        source_refs=s_refs,
        included_comparison_ids=tuple(r.comparison_id for r in export_payload.review_rows),
        review_decision_refs=tuple(d_refs),
        summary=export_payload.summary
    )

def _dataclass_to_dict(obj: Any) -> Any:
    """Helper to convert dataclasses to JSON-friendly dicts recursively."""
    if hasattr(obj, "__dataclass_fields__"):
        res = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            res[k] = _dataclass_to_dict(v)
        return res
    elif isinstance(obj, (tuple, list)):
        return [_dataclass_to_dict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    else:
        return obj

def build_comparator_review_summary_md(export_payload: ComparatorReviewExportPayload) -> str:
    """Generate a human-readable summary of the review results."""
    m = export_payload.manifest
    s = export_payload.summary
    
    lines = [
        f"# Comparator Review Summary",
        f"",
        f"- **Review Run ID:** `{m.review_run_id}`",
        f"- **Source Consensus Run:** `{m.source_consensus_run_id}`",
        f"- **Generated At:** {m.generated_at}",
        f"",
        f"## Triage Status Summary",
        f"| Status | Count |",
        f"| :--- | :--- |",
        f"| Annotated Rows | {s.n_annotated_rows} |",
        f"| Unreviewed | {s.n_unreviewed} |",
        f"| Reviewed | {s.n_reviewed} |",
        f"| Flagged | {s.n_flagged} |",
        f"| Handoff Candidate | {s.n_handoff_candidate} |",
        f"| **High Priority** | **{s.n_high_priority}** |",
        f"| **Follow-up Required** | **{s.n_follow_up_required}** |",
        f"",
        f"## Detailed Findings",
        f"### High Priority / Flagged Items",
    ]
    
    # Filter for interesting rows
    important_rows = [r for r in export_payload.review_rows if r.priority == "high" or r.triage_status == "flagged" or r.follow_up_required]
    
    if not important_rows:
        lines.append("No items flagged as high priority or requiring follow-up.")
    else:
        lines.append("| Comparison ID | Status | Priority | Follow-up | Note |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for r in important_rows[:50]:  # Cap at 50 for readability
            f_str = "Yes" if r.follow_up_required else "No"
            note_short = (r.review_note[:100] + "...") if len(r.review_note) > 100 else r.review_note
            lines.append(f"| `{r.comparison_id}` | {r.triage_status} | {r.priority} | {f_str} | {note_short or '-'} |")
            
        if len(important_rows) > 50:
            lines.append(f"*... and {len(important_rows)-50} more items.*")
            
    return "\n".join(lines)

def build_comparator_review_export_bundle(
    import_ctx: ConsensusBundleImportContext,
    session_ctx: ComparatorReviewSessionContext,
    annotation_store: ComparatorReviewAnnotationStore
) -> bytes:
    """Orchestrate the creation of the full review bundle ZIP archive."""
    
    review_run_id = build_comparator_review_run_id(session_ctx.source_consensus_run_id)
    review_bundle_filename = build_comparator_review_bundle_filename(review_run_id)
    
    # 1. Build Payloads
    export_payload = build_comparator_review_export_payload(import_ctx, session_ctx, annotation_store, review_run_id)
    handoff_payload = build_comparator_review_handoff_payload(
        import_ctx, session_ctx, annotation_store, export_payload, review_bundle_filename, review_run_id
    )
    
    # 2. Build Markdown
    summary_md = build_comparator_review_summary_md(export_payload)
    
    # 3. Create ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # JSON artifacts
        zf.writestr("review_manifest.json", json.dumps(_dataclass_to_dict(export_payload.manifest), indent=2))
        zf.writestr("review_rows.json", json.dumps(_dataclass_to_dict(export_payload.review_rows), indent=2))
        zf.writestr("review_summary.json", json.dumps(_dataclass_to_dict(export_payload.summary), indent=2))
        zf.writestr("review_handoff_contract.json", json.dumps(_dataclass_to_dict(handoff_payload), indent=2))
        
        # CSV artifact
        df = pd.DataFrame([_dataclass_to_dict(r) for r in export_payload.review_rows])
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        zf.writestr("review_rows.csv", csv_buf.getvalue())
        
        # Markdown artifact
        zf.writestr("review_summary.md", summary_md)
        
    return buf.getvalue()
