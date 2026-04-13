import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Optional

from iwa_rnaseq_reporter.legacy.analysis import (
    get_matrix_by_kind,
    add_display_labels,
)
from iwa_rnaseq_reporter.legacy.pca_utils import (
    select_top_variable_features,
    run_pca,
    build_pca_plot_df,
)
from iwa_rnaseq_reporter.legacy.correlation_utils import (
    compute_sample_correlation,
    build_sample_annotation_table,
)
from iwa_rnaseq_reporter.legacy.ui_utils import (
    format_display_df,
    get_nonempty_metadata_columns,
)
from iwa_rnaseq_reporter.legacy.gene_search import (
    build_feature_profile_table,
)
from iwa_rnaseq_reporter.legacy.feature_stats import (
    get_top_variable_features,
)
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext

"""
Plot Input Foundation Mapping:
- PCA Preview            -> AnalysisWorkspaceContext.analysis_matrix
- Sample Correlation     -> AnalysisWorkspaceContext.analysis_matrix
- Gene Search Profile    -> AnalysisWorkspaceContext.analysis_matrix (subset)
- Top Variable Features  -> AnalysisWorkspaceContext.analysis_matrix
"""


def render_analysis_matrix_summary(workspace: AnalysisWorkspaceContext):
    """
    Render Section 8 summaries: shape, filtering summary, and data preview.
    """
    st.write(
        f"**Selected analysis samples:** `{workspace.sample_count}` / "
        f"`{len(get_matrix_by_kind(workspace.dataset, workspace.matrix_kind).columns)}`"
    )

    st.dataframe(format_display_df(workspace.analysis_sample_table), use_container_width=True)

    st.write(
        f"**Analysis matrix shape:** `{workspace.feature_count}` features × `{workspace.sample_count}` samples"
    )

    with st.expander("Analysis Matrix Filtering Summary", expanded=False):
        st.write(f"- matrix_kind: `{workspace.matrix_kind}`")
        st.write(f"- log2p1: `{workspace.analysis_config.log2p1}`")
        st.write(f"- use_exclude: `{workspace.analysis_config.use_exclude}`")
        st.write(f"- min_feature_nonzero_samples: `{workspace.analysis_config.min_feature_nonzero_samples}`")
        st.write(f"- min_feature_mean: `{workspace.analysis_config.min_feature_mean}`")

    with st.expander("Analysis Matrix Preview", expanded=False):
        # Show labeled preview for wet-first usability
        labeled_preview = add_display_labels(workspace.analysis_matrix.head(10), workspace.dataset.feature_annotation)
        # Reorder to show labels first
        pref_cols = ["display_label", "gene_symbol", "feature_id"]
        other_cols = [c for c in labeled_preview.columns if c not in pref_cols]
        labeled_preview = labeled_preview[pref_cols + other_cols]
        st.dataframe(format_display_df(labeled_preview), use_container_width=True)


def render_pca_preview_section(workspace: AnalysisWorkspaceContext):
    """
    Render Section 9: PCA Preview.
    (SOT: workspace.analysis_matrix)
    """
    st.header("9. PCA Preview")
    
    p1, p2, p3 = st.columns(3)
    with p1:
        run_pca_flag = st.checkbox("Enable PCA preview", value=True)
    with p2:
        pca_scale = st.checkbox("Scale features before PCA", value=False)
    with p3:
        top_variable_features = st.number_input(
            "Top variable features for PCA",
            min_value=10,
            max_value=5000,
            value=500,
            step=50,
        )

    if run_pca_flag:
        try:
            num_analysis_samples = workspace.sample_count
            if num_analysis_samples < 2:
                st.warning("PCA preview requires at least 2 selected samples.")
            else:
                if num_analysis_samples == 2:
                    st.warning(
                        "PCA preview with 2 samples should be interpreted as a simple distance-like overview."
                    )

                pca_input = select_top_variable_features(
                    workspace.analysis_matrix,
                    top_n=int(top_variable_features),
                )

                pca_scores_df, explained = run_pca(
                    pca_input,
                    n_components=5,
                    scale=pca_scale,
                )

                pca_plot_df = build_pca_plot_df(
                    workspace.dataset,
                    pca_scores_df,
                    explained_variance_ratio=explained,
                    use_exclude=workspace.analysis_config.use_exclude,
                )

                st.write(
                    f"**PCA input shape:** `{pca_input.shape[0]}` features × `{pca_input.shape[1]}` samples"
                )

                if len(explained) >= 2:
                    st.write(
                        f"**Explained variance:** PC1 = `{explained[0] * 100:.2f}%`, "
                        f"PC2 = `{explained[1] * 100:.2f}%`"
                    )
                elif len(explained) == 1:
                    st.write(f"**Explained variance:** PC1 = `{explained[0] * 100:.2f}%`")

                metadata_color_candidates = get_nonempty_metadata_columns(
                    pca_plot_df,
                    ["group", "condition", "batch", "color", "sample_id"],
                )

                color_col = None
                if metadata_color_candidates:
                    color_col = st.selectbox(
                        "Color PCA points by",
                        options=metadata_color_candidates,
                        index=0,
                        key="pca_color_col"
                    )

                # Use Plotly for PCA
                pc1_label = pca_plot_df.attrs.get("pc1_label", "PC1")
                pc2_label = pca_plot_df.attrs.get("pc2_label", "PC2")

                fig = px.scatter(
                    pca_plot_df,
                    x="PC1",
                    y="PC2",
                    color=color_col,
                    hover_data=["sample_id", "display_name", "group", "condition"],
                    labels={"PC1": pc1_label, "PC2": pc2_label},
                    title=f"PCA: {pc1_label} vs {pc2_label}",
                    template="plotly_white",
                )
                fig.update_traces(marker=dict(size=12, line=dict(width=1, color="DarkSlateGrey")))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("PCA Table", expanded=False):
                    st.dataframe(format_display_df(pca_plot_df), use_container_width=True)

        except Exception as e:
            st.error(f"Failed to run PCA preview: {e}")


def render_sample_correlation_section(workspace: AnalysisWorkspaceContext):
    """
    Render Section 10: Sample Correlation.
    (SOT: workspace.analysis_matrix)
    """
    st.header("10. Sample Correlation")
    
    corr_method = st.selectbox(
        "Correlation method",
        options=["pearson", "spearman"],
        index=0,
    )

    try:
        corr_df = compute_sample_correlation(
            workspace.analysis_matrix,
            method=corr_method,
        )

        st.write(
            f"**Correlation matrix shape:** `{corr_df.shape[0]}` × `{corr_df.shape[1]}`"
        )
        st.caption("Sample-to-sample correlation computed from the current analysis matrix.")

        st.subheader("Correlation Table")
        st.dataframe(format_display_df(corr_df), use_container_width=True)

        st.subheader("Correlation Heatmap")
        st.dataframe(
            corr_df.style.background_gradient(axis=None),
            use_container_width=True,
        )

        with st.expander("Sample Annotation Table", expanded=False):
            ann_df = build_sample_annotation_table(workspace.dataset, list(corr_df.columns))
            st.dataframe(format_display_df(ann_df), use_container_width=True)

    except Exception as e:
        st.error(f"Failed to compute sample correlation: {e}")


def render_gene_search_section(workspace: AnalysisWorkspaceContext):
    """
    Render Section 11: Gene Search.
    (SOT: workspace.analysis_matrix index)
    """
    st.header("11. Gene Search")
    
    search_query = st.text_input("Search for Gene/Feature ID or Symbol", placeholder="e.g. ACT1 or YAL001C")
    if search_query:
        # Standardized: Build search index with display labels
        search_base = pd.DataFrame({"feature_id": workspace.analysis_matrix.index})
        search_df = add_display_labels(search_base, workspace.dataset.feature_annotation)
        
        query = search_query.lower()
        mask = (
            search_df["feature_id"].str.lower().str.contains(query) | 
            search_df["gene_symbol"].fillna("").str.lower().str.contains(query)
        )
        hits_df = search_df[mask].head(50)
        
        if hits_df.empty:
            st.info(f"No matches found for '{search_query}'")
        else:
            hit_map = {row["feature_id"]: f"{row['display_label']} ({row['feature_id']})" for _, row in hits_df.iterrows()}
            selected_id = st.selectbox(f"Found {len(hits_df)} matches", options=list(hit_map.keys()), format_func=lambda x: hit_map[x])
            if selected_id:
                try:
                    profile_df = build_feature_profile_table(
                        workspace.dataset,
                        selected_id,
                        matrix_kind=workspace.matrix_kind,
                        log2p1=workspace.analysis_config.log2p1,
                        use_exclude=workspace.analysis_config.use_exclude,
                        min_feature_nonzero_samples=workspace.analysis_config.min_feature_nonzero_samples,
                        min_feature_mean=workspace.analysis_config.min_feature_mean,
                    )

                    st.subheader(f"Profile: {hit_map[selected_id]}")
                    
                    # Simple bar chart for expression
                    st.bar_chart(profile_df, x="sample_id", y="expression_value", color="group" if "group" in profile_df.columns else None)

                    with st.expander("Show Profile Table", expanded=False):
                        st.dataframe(format_display_df(profile_df), use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to build profile for {selected_id}: {e}")


def render_top_variable_features_section(workspace: AnalysisWorkspaceContext):
    """
    Render Section 12: Top Variable Features.
    (SOT: workspace.analysis_matrix)
    """
    st.header("12. Top Variable Features")
    
    top_n_stats = st.number_input("Show top N variable features", min_value=5, max_value=500, value=50, step=5)
    
    try:
        top_stats_df = get_top_variable_features(workspace.analysis_matrix, top_n=int(top_n_stats))
        # Align with display_label contract
        top_stats_df = add_display_labels(top_stats_df, workspace.dataset.feature_annotation)
        
        # Reorder for display
        pref_stats = ["display_label", "gene_symbol", "feature_id", "mean", "variance", "nonzero_samples", "max_value"]
        display_cols_stats = [c for c in pref_stats if c in top_stats_df.columns]
        top_stats_df = top_stats_df[display_cols_stats]
        
        st.write(f"Top {len(top_stats_df)} features by variance in the current analysis matrix.")
        st.dataframe(format_display_df(top_stats_df), use_container_width=True)
    except Exception as e:
        st.error(f"Failed to compute feature statistics: {e}")
