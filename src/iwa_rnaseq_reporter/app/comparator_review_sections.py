import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewSessionContext,
    ComparatorReviewRowSpec
)
from iwa_rnaseq_reporter.app.comparator_consensus_import import ConsensusBundleImportContext
from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import read_consensus_bundle
from iwa_rnaseq_reporter.app.comparator_review_session_builder import build_comparator_review_session_context
from iwa_rnaseq_reporter.app.comparator_review_table import ComparatorReviewFilterSpec, ComparatorReviewTableContext
from iwa_rnaseq_reporter.app.comparator_review_table_builder import (
    build_comparator_review_table_context,
    build_comparator_review_table_dataframe
)
from iwa_rnaseq_reporter.app.comparator_review_drilldown_builder import build_comparator_review_drilldown_context
from iwa_rnaseq_reporter.app.comparator_review_annotation import ComparatorReviewAnnotationSpec, ComparatorReviewAnnotationStore
from iwa_rnaseq_reporter.app.comparator_review_annotation_builder import (
    build_empty_comparator_review_annotation_store,
    upsert_comparator_review_annotation,
    remove_comparator_review_annotation,
    get_comparator_review_annotation,
    build_comparator_review_annotation_summary
)

def _render_summary_counters(ctx: ComparatorReviewTableContext, ann_store: Optional[ComparatorReviewAnnotationStore] = None):
    """
    Display session and filtered summary metrics.
    Incl. v0.20.4 annotation progress if store provided.
    """
    col1, col2, col3, col4 = st.columns(4)
    sum_f = ctx.summary
    
    with col1:
        st.metric("Total Comparisons", f"{sum_f.n_total_rows}")
        st.metric("Filtered Matches", f"{sum_f.n_filtered_rows}")
        
    with col2:
        st.metric("Consensus", f"{sum_f.n_consensus}")
        st.metric("No Consensus", f"{sum_f.n_no_consensus}")
        
    with col3:
        st.metric("Insufficient Evidence", f"{sum_f.n_insufficient_evidence}")
        st.metric("With Conflict", f"{sum_f.n_with_conflict}")
        
    with col4:
        st.metric("Weak Support", f"{sum_f.n_with_weak_support}")

    if ann_store and ann_store.summary:
        st.markdown("---")
        st.markdown("**Review Progress & Annotation Summary**")
        a1, a2, a3, a4 = st.columns(4)
        s = ann_store.summary
        a1.metric("Annotated", f"{s.n_annotated_rows}")
        a1.metric("Unreviewed", f"{s.n_unreviewed}")
        a2.metric("Reviewed", f"{s.n_reviewed}")
        a2.metric("Flagged", f"{s.n_flagged}")
        a3.metric("Handoff Candidates", f"{s.n_handoff_candidate}")
        a3.metric("High Priority", f"{s.n_high_priority}")
        a4.metric("Follow-up Required", f"{s.n_follow_up_required}")

def render_comparator_review_table_section():
    """
    Main entry for Consensus Review Table section.
    Corresponds to spec 258-364.
    """
    st.header("Consensus Review Table")
    st.markdown("Examine and triage consensus results from comparative analysis.")
    
    # Bundle Intake (spec 285-308, v0.20.3 refactor)
    with st.expander("Import Consensus Bundle", expanded=st.session_state.get("comparator_review_session_context") is None):
        manifest_path = st.text_input(
            "Consensus Manifest Path",
            value=st.session_state.get("comparator_review_bundle_manifest_path", ""),
            key="review_bundle_manifest_input"
        )
        if st.button("Load Review Session"):
            try:
                # v0.20.3: One-time bundle read to keep import_ctx for inspection
                import_ctx = read_consensus_bundle(manifest_path)
                session_ctx = build_comparator_review_session_context(import_ctx)
                
                st.session_state["comparator_review_import_context"] = import_ctx
                st.session_state["comparator_review_session_context"] = session_ctx
                st.session_state["comparator_review_bundle_manifest_path"] = manifest_path
                
                # v0.20.4: Initialize fresh annotation store for the new session
                st.session_state["comparator_review_annotation_store"] = build_empty_comparator_review_annotation_store(session_ctx)
                
                st.success(f"Successfully loaded {len(session_ctx.rows)} comparisons")
            except Exception as e:
                st.error(f"Failed to load bundle: {e}")
                
    session_ctx: Optional[ComparatorReviewSessionContext] = st.session_state.get("comparator_review_session_context")
    if not session_ctx:
        st.info("Please load a consensus bundle to begin review.")
        return
        
    # Filter Panel (spec 310-333)
    st.subheader("Filter Controls")
    
    # 1. Gather options from session rows
    all_rows = session_ctx.rows
    status_options = sorted(list(set(r.decision_status for r in all_rows)))
    
    label_map = {}
    for r in all_rows:
        if r.decided_label_key:
            disp = r.decided_label_display or r.decided_label_key
            label_map[r.decided_label_key] = disp
            
    sorted_label_keys = sorted(label_map.keys(), key=lambda k: label_map[k])
    
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        sel_statuses = st.multiselect("Decision Status", options=status_options)
        sel_labels = st.multiselect(
            "Decided Label", 
            options=sorted_label_keys,
            format_func=lambda k: label_map.get(k, k)
        )
        
    with f_col2:
        c_mode = st.selectbox(
            "Conflict Mode", 
            options=["all", "conflict_only", "no_conflict_only"],
            format_func=lambda m: "All" if m=="all" else "Conflict Only" if m=="conflict_only" else "No Conflict"
        )
        w_mode = st.selectbox(
            "Weak Support Mode",
            options=["all", "weak_only", "not_weak_only"],
            format_func=lambda m: "All" if m=="all" else "Weak Only" if m=="weak_only" else "Not Weak Only"
        )
        
    search_query = st.text_input("Free Text Search", placeholder="Search by ID, Label, Reason...")
    
    # Apply Filters (spec 117-123)
    filters = ComparatorReviewFilterSpec(
        decision_statuses=tuple(sel_statuses),
        decided_label_keys=tuple(sel_labels),
        conflict_mode=c_mode,
        weak_support_mode=w_mode,
        search_query=search_query
    )
    
    table_ctx = build_comparator_review_table_context(session_ctx, filters)
    
    # Render Summary (spec 335-353, v0.20.4 extended)
    st.divider()
    ann_store: Optional[ComparatorReviewAnnotationStore] = st.session_state.get("comparator_review_annotation_store")
    _render_summary_counters(table_ctx, ann_store)
    st.divider()
    
    # Render Table (spec 355-364)
    if not table_ctx.filtered_rows:
        st.warning("No comparisons matched the current filters.")
        return
        
    df = build_comparator_review_table_dataframe(table_ctx.filtered_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # Drilldown Pane (v0.20.3)
    # --------------------------------------------------
    st.divider()
    st.subheader("Inspection & Drilldown")
    
    # 1. Selection based on filtered rows
    f_rows = table_ctx.filtered_rows
    selection_options = [r.comparison_id for r in f_rows]
    
    selected_comp_id = st.selectbox(
        "Select Comparison to Inspect",
        options=selection_options,
        format_func=lambda cid: next(
            (f"{r.comparison_id} | {r.decision_status} | {r.decided_label_display or r.decided_label_key or '-'}" 
             for r in f_rows if r.comparison_id == cid), 
            cid
        )
    )
    
    import_ctx: Optional[ConsensusBundleImportContext] = st.session_state.get("comparator_review_import_context")
    
    if selected_comp_id and import_ctx:
        try:
            drilldown_ctx = build_comparator_review_drilldown_context(import_ctx, session_ctx, selected_comp_id)
            d = drilldown_ctx.decision_detail
            
            # A. Decision Summary Card
            st.markdown(f"### Details: `{d.comparison_id}`")
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", d.decision_status)
            c2.metric("Decided Label", d.decided_label_display or d.decided_label_key or "-")
            c3.metric("Support Margin", f"{d.support_margin:.4f}" if d.support_margin is not None else "-")
            
            s1, s2, s3 = st.columns(3)
            s1.write(f"**Supporting Refs:** {d.n_supporting_refs}")
            s2.write(f"**Conflicting Refs:** {d.n_conflicting_refs}")
            s3.write(f"**Competing Candidates:** {d.n_competing_candidates or '-'}")
            
            if d.has_conflict:
                st.warning("⚠️ Conflict detected in evidence.")
            if d.has_weak_support:
                st.info("ℹ️ Weak support from references.")
            
            if d.reason_codes:
                st.write("**Reason Codes:**", ", ".join(d.reason_codes))
                
            # B. Reference Tables
            t1, t2 = st.tabs(["Supporting References", "Conflicting References"])
            with t1:
                if d.top_supporting_refs:
                    sup_df = pd.DataFrame([vars(r) for r in d.top_supporting_refs])
                    st.dataframe(sup_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No supporting references.")
            with t2:
                if d.top_conflicting_refs:
                    con_df = pd.DataFrame([vars(r) for r in d.top_conflicting_refs])
                    st.dataframe(con_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No conflicting references.")
            
            # C. Artifact Pointers
            with st.expander("Artifact Pointers", expanded=False):
                st.write("**Decisions (JSON):**", d.artifacts.consensus_decisions_json_path or "-")
                st.write("**Evidence Profile (JSON):**", d.artifacts.evidence_profiles_json_path or "-")
                st.write("**Summary (MD):**", d.artifacts.report_summary_md_path or "-")
                st.write("**Handoff (JSON):**", d.artifacts.consensus_handoff_contract_path or "-")

            # D. Raw JSON Inspection
            with st.expander("Raw JSON Inspection", expanded=False):
                j1, j2 = st.tabs(["Decision Payload", "Evidence Profile"])
                with j1:
                    if drilldown_ctx.json_inspection.decision_json:
                        st.json(drilldown_ctx.json_inspection.decision_json)
                    else:
                        st.info("No decision JSON available.")
                with j2:
                    if drilldown_ctx.json_inspection.evidence_profile_json:
                        st.json(drilldown_ctx.json_inspection.evidence_profile_json)
                    else:
                        st.info("No evidence profile JSON available.")
            
            if drilldown_ctx.issues:
                for issue in drilldown_ctx.issues:
                    st.error(f"Issue: {issue}")

            # E. Review Annotation Form (v0.20.4)
            st.divider()
            st.subheader("Reviewer Annotation & Triage")
            
            # Fetch current annotation if exists
            current_ann = None
            if ann_store:
                current_ann = get_comparator_review_annotation(ann_store, selected_comp_id)
            
            if current_ann:
                st.info(f"**Current Status:** {current_ann.triage_status.upper()} | **Priority:** {current_ann.priority.upper()}")
                if current_ann.review_note:
                    st.markdown(f"> **Note:** {current_ann.review_note}")
                if current_ann.follow_up_required:
                    st.warning("Needs follow-up.")

            with st.form("annotation_form", clear_on_submit=False):
                # Default values from current annotation
                def_status = "unreviewed"
                def_priority = "normal"
                def_note = ""
                def_follow = False
                
                if current_ann:
                    def_status = current_ann.triage_status
                    def_priority = current_ann.priority
                    def_note = current_ann.review_note
                    def_follow = current_ann.follow_up_required

                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    t_status = st.selectbox(
                        "Triage Status",
                        options=["unreviewed", "flagged", "reviewed", "handoff_candidate"],
                        index=["unreviewed", "flagged", "reviewed", "handoff_candidate"].index(def_status),
                        format_func=lambda s: s.replace("_", " ").title()
                    )
                with t_col2:
                    t_priority = st.selectbox(
                        "Priority",
                        options=["normal", "high"],
                        index=["normal", "high"].index(def_priority),
                        format_func=lambda s: s.title()
                    )
                
                t_follow = st.checkbox("Follow-up Required", value=def_follow)
                t_note = st.text_area("Review Note / Context", value=def_note, placeholder="Add research notes or justification for triage...")
                
                save_col, clear_col, _ = st.columns([1, 1, 2])
                with save_col:
                    save_btn = st.form_submit_button("Save Annotation")
                with clear_col:
                    clear_btn = st.form_submit_button("Clear Annotation")
                    
                if save_btn:
                    new_ann = ComparatorReviewAnnotationSpec(
                        comparison_id=selected_comp_id,
                        triage_status=t_status,
                        priority=t_priority,
                        review_note=t_note,
                        follow_up_required=t_follow
                    )
                    try:
                        new_store = upsert_comparator_review_annotation(ann_store, session_ctx, new_ann)
                        st.session_state["comparator_review_annotation_store"] = new_store
                        st.success(f"Annotation saved for {selected_comp_id}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
                        
                if clear_btn:
                    try:
                        new_store = remove_comparator_review_annotation(ann_store, session_ctx, selected_comp_id)
                        st.session_state["comparator_review_annotation_store"] = new_store
                        st.success(f"Annotation cleared for {selected_comp_id}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to clear: {e}")

        except Exception as e:
            st.error(f"Failed to build drilldown details: {e}")
    elif not selected_comp_id:
        st.caption("Select a comparison from the list above to view detail evidence.")
