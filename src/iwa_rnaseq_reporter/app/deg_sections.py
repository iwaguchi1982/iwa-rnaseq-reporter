import streamlit as st
from typing import Optional, Any, Tuple

from iwa_rnaseq_reporter.legacy.analysis import (
    build_analysis_sample_table,
)
from iwa_rnaseq_reporter.legacy.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
    build_comparison_sample_table,
)
from iwa_rnaseq_reporter.legacy.ui_utils import (
    format_display_df,
)
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext


def render_deg_comparison_design_section(
    workspace: AnalysisWorkspaceContext
) -> Tuple[Optional[Any], Optional[str], Optional[str], Optional[str]]:
    """
    Render Section 13: DEG Comparison Design.
    
    Returns:
        (deg_input_obj, comparison_column, group_a, group_b)
    """
    st.header("13. DEG Comparison Design")

    st.info(
        f"Comparison design uses the current analysis matrix and included samples.  \n"
        f"**Current Settings:** `{workspace.matrix_kind}` / `log2p1={workspace.analysis_config.log2p1}` / "
        f"`use_exclude={workspace.analysis_config.use_exclude}` / "
        f"`min_nonzero={workspace.analysis_config.min_feature_nonzero_samples}` / "
        f"`min_mean={workspace.analysis_config.min_feature_mean}`"
    )

    comparison_sample_table = build_analysis_sample_table(
        workspace.dataset,
        matrix_kind=workspace.matrix_kind,
        use_exclude=workspace.analysis_config.use_exclude,
    )

    # In v0.1.4, candidate columns are explicitly derived from included samples
    comparison_candidate_columns = get_comparison_candidate_columns(comparison_sample_table)

    if not comparison_candidate_columns:
        st.warning("No comparison-ready metadata columns were found among the currently included samples.")
        return None, None, None, None

    d1, d2, d3 = st.columns(3)
    with d1:
        comparison_column = st.selectbox(
            "Comparison column",
            options=comparison_candidate_columns,
            index=0,
            key="deg_comparison_col"
        )

    group_summary = summarize_groups(comparison_sample_table, comparison_column)
    valid_group_names = group_summary["group_name"].tolist()

    if len(valid_group_names) < 2:
        st.warning(
            f"Selected column '{comparison_column}' does not have at least 2 non-empty groups "
            "in the current analysis set."
        )
        return None, comparison_column, None, None

    with d2:
        group_a = st.selectbox(
            "Group A (Case)",
            options=valid_group_names,
            index=0,
            key="deg_group_a"
        )

    remaining_groups = [g for g in valid_group_names if g != group_a]
    with d3:
        group_b = st.selectbox(
            "Group B (Control)",
            options=remaining_groups,
            index=0 if remaining_groups else None,
            key="deg_group_b"
        )

    st.subheader("Group Summary (Included Samples)")
    st.dataframe(format_display_df(group_summary), use_container_width=True)

    try:
        deg_input_obj = build_deg_input(
            workspace.dataset,
            matrix_kind=workspace.matrix_kind,
            group_column=comparison_column,
            group_a=group_a,
            group_b=group_b,
            log2p1=workspace.analysis_config.log2p1,
            use_exclude=workspace.analysis_config.use_exclude,
            min_feature_nonzero_samples=workspace.analysis_config.min_feature_nonzero_samples,
            min_feature_mean=workspace.analysis_config.min_feature_mean,
        )

        issues = validate_deg_input(deg_input_obj, min_samples_per_group=2)

        st.write(
            f"**Comparison samples:** `{len(deg_input_obj.feature_matrix.columns)}` "
            f"(`{group_a}`: {len(deg_input_obj.group_a_samples)}, "
            f"`{group_b}`: {len(deg_input_obj.group_b_samples)})"
        )

        if issues:
            st.warning("Comparison design has validation issues:")
            for issue in issues:
                st.warning(issue)
        else:
            st.success("Comparison design looks ready for DEG preview.")

        with st.expander("Comparison Sample Table", expanded=False):
            st.dataframe(
                format_display_df(build_comparison_sample_table(deg_input_obj)),
                use_container_width=True,
            )
        
        return deg_input_obj, comparison_column, group_a, group_b

    except Exception as e:
        st.error(f"Failed to build comparison design: {e}")
        return None, comparison_column, group_a, group_b
