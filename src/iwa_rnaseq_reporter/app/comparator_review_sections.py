import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewSessionContext,
    ComparatorReviewRowSpec
)
from iwa_rnaseq_reporter.app.comparator_review_session_builder import build_comparator_review_session_context_from_bundle
from iwa_rnaseq_reporter.app.comparator_review_table import ComparatorReviewFilterSpec, ComparatorReviewTableContext
from iwa_rnaseq_reporter.app.comparator_review_table_builder import (
    build_comparator_review_table_context,
    build_comparator_review_table_dataframe
)

def _render_summary_counters(ctx: ComparatorReviewTableContext):
    """
    Display session and filtered summary metrics.
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
        # Note: can add more if space allows or use a second row as per spec 347.

def render_comparator_review_table_section():
    """
    Main entry for Consensus Review Table section.
    Corresponds to spec 258-364.
    """
    st.header("Consensus Review Table")
    st.markdown("Examine and triage consensus results from comparative analysis.")
    
    # Bundle Intake (spec 285-308)
    with st.expander("Import Consensus Bundle", expanded=st.session_state.get("comparator_review_session_context") is None):
        manifest_path = st.text_input(
            "Consensus Manifest Path",
            value=st.session_state.get("comparator_review_bundle_manifest_path", ""),
            key="review_bundle_manifest_input"
        )
        if st.button("Load Review Session"):
            try:
                session_ctx = build_comparator_review_session_context_from_bundle(manifest_path)
                st.session_state["comparator_review_session_context"] = session_ctx
                st.session_state["comparator_review_bundle_manifest_path"] = manifest_path
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
    
    # Render Summary (spec 335-353)
    st.divider()
    _render_summary_counters(table_ctx)
    st.divider()
    
    # Render Table (spec 355-364)
    if not table_ctx.filtered_rows:
        st.warning("No comparisons matched the current filters.")
        return
        
    df = build_comparator_review_table_dataframe(table_ctx.filtered_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
