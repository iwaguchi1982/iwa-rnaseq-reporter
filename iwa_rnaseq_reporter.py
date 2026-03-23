import streamlit as st
import pandas as pd
from pathlib import Path

from src.loader import load_reporter_dataset, ReporterLoadError
from src.analysis import (
    get_matrix_by_kind,
    get_analysis_sample_ids,
    build_analysis_matrix,
    build_analysis_sample_table,
)
from src.pca_utils import (
    select_top_variable_features,
    run_pca,
    build_pca_plot_df,
)
from src.correlation_utils import (
    compute_sample_correlation,
    build_sample_annotation_table,
)
from src.ui_utils import (
    format_display_df,
    get_nonempty_metadata_columns,
)
from src.gene_search import (
    search_features,
    build_feature_profile_table,
)
from src.feature_stats import (
    compute_feature_statistics,
    get_top_variable_features,
)
from src.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
)
from src.deg_preview import (
    build_deg_preview_table,
    summarize_deg_preview,
)
import plotly.express as px

st.set_page_config(page_title="iwa-rnaseq-reporter", layout="wide")
st.title("iwa-rnaseq-reporter")


def reorder_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "sample_id",
        "display_name",
        "group",
        "condition",
        "replicate",
        "batch",
        "pair_id",
        "color",
        "exclude",
        "note",
    ]
    ordered = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in ordered]
    return df[ordered + remaining]


def build_file_status_df(ds) -> pd.DataFrame:
    rows = []

    required_keys = ["sample_metadata", "sample_qc_summary", "gene_tpm", "gene_numreads", "run_summary"]
    optional_keys = ["transcript_tpm", "transcript_numreads", "sample_sheet", "run_config", "run_log"]

    for key in required_keys:
        path = ds.resolved_paths.get(key)
        rows.append(
            {
                "file_key": key,
                "required": "yes",
                "status": "found" if path and path.exists() else "missing",
                "resolved_path": str(path) if path else "-",
            }
        )

    for key in optional_keys:
        path = ds.resolved_paths.get(key)
        rows.append(
            {
                "file_key": key,
                "required": "no",
                "status": "found" if path and path.exists() else "missing",
                "resolved_path": str(path) if path else "-",
            }
        )

    return pd.DataFrame(rows)


def build_validation_df(ds) -> pd.DataFrame:
    if not ds.messages:
        return pd.DataFrame(columns=["level", "code", "message"])
    return pd.DataFrame(
        [{"level": m.level, "code": m.code, "message": m.message} for m in ds.messages]
    )


# --------------------------------------------------
# 1. Input
# --------------------------------------------------
st.header("1. Input")
input_path_str = st.text_input(
    "Dataset or Manifest Path",
    placeholder="/path/to/run_dir or /path/to/results_dir or /path/to/dataset_manifest.json",
)

if st.button("Load Dataset"):
    if not input_path_str:
        st.error("Please provide a path.")
    else:
        input_path = Path(input_path_str)
        try:
            ds = load_reporter_dataset(input_path)
            st.session_state["dataset"] = ds
            st.success("Successfully loaded dataset!")
        except ReporterLoadError as e:
            st.error("Failed to load dataset.")
            for msg in e.messages:
                if msg.level == "fatal":
                    st.error(f"FATAL [{msg.code}]: {msg.message}")
                elif msg.level == "warning":
                    st.warning(f"WARNING [{msg.code}]: {msg.message}")
                else:
                    st.info(f"INFO [{msg.code}]: {msg.message}")
        except Exception as e:
            st.exception(e)

if "dataset" in st.session_state:
    ds = st.session_state["dataset"]

    # --------------------------------------------------
    # 2. Load Status
    # --------------------------------------------------
    st.header("2. Load Status")

    required_keys = ["sample_metadata", "sample_qc_summary", "gene_tpm", "gene_numreads", "run_summary"]
    optional_keys = ["transcript_tpm", "transcript_numreads", "sample_sheet", "run_config", "run_log"]

    found_required = sum(1 for k in required_keys if ds.resolved_paths.get(k) and ds.resolved_paths[k].exists())
    found_optional = sum(1 for k in optional_keys if ds.resolved_paths.get(k) and ds.resolved_paths[k].exists())

    warning_count = sum(1 for m in ds.messages if m.level == "warning")
    info_count = sum(1 for m in ds.messages if m.level == "info")

    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Resolved Input Type:** `{ds.input_type}`")
    c2.write(f"**Required Files:** `{found_required} / {len(required_keys)}`")
    c3.write(f"**Optional Files:** `{found_optional} / {len(optional_keys)}`")
    c4.write(f"**Transcript Matrices:** `{'available' if ds.transcript_tpm is not None else 'not available'}`")

    st.write(f"**Manifest Path:** `{ds.manifest_path}`")
    st.write(f"**Run Directory:** `{ds.base_dir}`")
    st.write(f"**Validation Warnings:** `{warning_count}` | **Info:** `{info_count}`")

    with st.expander("File Status Details", expanded=False):
        st.dataframe(build_file_status_df(ds), use_container_width=True)

    # --------------------------------------------------
    # 3. Dataset Overview
    # --------------------------------------------------
    st.header("3. Dataset Overview")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Run Name", ds.run_name)
        st.metric("Total Samples (metadata)", len(ds.sample_metadata))
    with col2:
        st.metric("Dataset ID", ds.dataset_id)
        st.metric("Samples in Matrix", len(ds.gene_tpm.columns))
    with col3:
        st.metric("Gene Features", len(ds.gene_tpm))
        st.metric("Transcript Features", len(ds.transcript_tpm) if ds.transcript_tpm is not None else 0)

    # --------------------------------------------------
    # 4. Sample ID Summary
    # --------------------------------------------------
    st.header("4. Sample ID Summary")

    s1, s2, s3 = st.columns(3)
    s1.write(f"**Aggregated:** {len(ds.sample_ids_aggregated)}")
    s2.write(f"**Success:** {len(ds.sample_ids_success)}")
    s3.write(f"**Failed:** {len(ds.sample_ids_failed)}")

    with st.expander("Show Sample ID Lists", expanded=False):
        ex1, ex2, ex3 = st.columns(3)
        ex1.write("**Aggregated IDs**")
        ex1.code(", ".join(ds.sample_ids_aggregated) if ds.sample_ids_aggregated else "None")

        ex2.write("**Success IDs**")
        ex2.code(", ".join(ds.sample_ids_success) if ds.sample_ids_success else "None")

        ex3.write("**Failed IDs**")
        ex3.code(", ".join(ds.sample_ids_failed) if ds.sample_ids_failed else "None")

    # --------------------------------------------------
    # 5. Validation Messages
    # --------------------------------------------------
    st.header("5. Validation Messages")

    if ds.messages:
        fatal_count = sum(1 for m in ds.messages if m.level == "fatal")
        warning_count = sum(1 for m in ds.messages if m.level == "warning")
        info_count = sum(1 for m in ds.messages if m.level == "info")

        st.write(f"Fatal: `{fatal_count}` | Warning: `{warning_count}` | Info: `{info_count}`")
        st.dataframe(build_validation_df(ds), use_container_width=True)
    else:
        st.success("No validation messages.")

    # --------------------------------------------------
    # 6. Sample Metadata
    # --------------------------------------------------
    st.header("6. Sample Metadata")
    display_metadata = reorder_metadata_columns(format_display_df(ds.sample_metadata.copy()))
    st.dataframe(display_metadata.head(10), use_container_width=True)

    # --------------------------------------------------
    # 7. Sample QC Summary
    # --------------------------------------------------
    st.header("7. Sample QC Summary")

    if "mapping_rate" in ds.sample_qc_summary.columns:
        mapping_series = pd.to_numeric(ds.sample_qc_summary["mapping_rate"], errors="coerce")
        q1, q2, q3 = st.columns(3)
        q1.metric("Avg Mapping Rate", f"{mapping_series.mean():.4f}" if mapping_series.notna().any() else "NA")
        q2.metric("Min Mapping Rate", f"{mapping_series.min():.4f}" if mapping_series.notna().any() else "NA")
        q3.metric("Max Mapping Rate", f"{mapping_series.max():.4f}" if mapping_series.notna().any() else "NA")

    if "qc_status" in ds.sample_qc_summary.columns:
        qc_counts = ds.sample_qc_summary["qc_status"].astype(str).value_counts(dropna=False)
        st.write("**QC Status Counts**")
        st.dataframe(
            qc_counts.rename_axis("qc_status").reset_index(name="count"),
            use_container_width=True,
        )

    st.dataframe(format_display_df(ds.sample_qc_summary.head(10)), use_container_width=True)

    # --------------------------------------------------
    # 8. Analysis Setup
    # --------------------------------------------------
    st.header("8. Analysis Setup")

    available_matrix_options = ["gene_tpm", "gene_numreads"]
    if ds.transcript_tpm is not None:
        available_matrix_options.append("transcript_tpm")
    if ds.transcript_numreads is not None:
        available_matrix_options.append("transcript_numreads")

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        matrix_kind = st.selectbox("Matrix kind", options=available_matrix_options, index=0)
    with a2:
        log2p1 = st.checkbox("Apply log2(x+1)", value=True)
    with a3:
        use_exclude = st.checkbox("Respect exclude column", value=True)
    with a4:
        min_feature_nonzero_samples = st.number_input(
            "Min nonzero samples per feature",
            min_value=1,
            max_value=max(1, len(get_matrix_by_kind(ds, matrix_kind).columns)),
            value=1,
            step=1,
        )

    min_feature_mean = st.number_input(
        "Min feature mean",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )

    try:
        analysis_sample_ids = get_analysis_sample_ids(
            ds,
            matrix_kind=matrix_kind,
            use_exclude=use_exclude,
        )

        analysis_sample_table = build_analysis_sample_table(
            ds,
            matrix_kind=matrix_kind,
            use_exclude=use_exclude,
        )

        st.write(
            f"**Selected analysis samples:** `{len(analysis_sample_ids)}` / "
            f"`{len(get_matrix_by_kind(ds, matrix_kind).columns)}`"
        )

        st.dataframe(format_display_df(analysis_sample_table), use_container_width=True)

        analysis_matrix = build_analysis_matrix(
            ds,
            matrix_kind=matrix_kind,
            log2p1=log2p1,
            use_exclude=use_exclude,
            min_feature_nonzero_samples=int(min_feature_nonzero_samples),
            min_feature_mean=float(min_feature_mean),
        )

        st.write(
            f"**Analysis matrix shape:** `{analysis_matrix.shape[0]}` features × `{analysis_matrix.shape[1]}` samples"
        )

        with st.expander("Analysis Matrix Filtering Summary", expanded=False):
            st.write(f"- matrix_kind: `{matrix_kind}`")
            st.write(f"- log2p1: `{log2p1}`")
            st.write(f"- use_exclude: `{use_exclude}`")
            st.write(f"- min_feature_nonzero_samples: `{min_feature_nonzero_samples}`")
            st.write(f"- min_feature_mean: `{min_feature_mean}`")

        with st.expander("Analysis Matrix Preview", expanded=False):
            st.dataframe(analysis_matrix.head(10), use_container_width=True)

    except Exception as e:
        st.error(f"Failed to prepare analysis matrix: {e}")
        analysis_matrix = None

    # --------------------------------------------------
    # 9. PCA Preview
    # --------------------------------------------------
    st.header("9. PCA Preview")

    if analysis_matrix is not None:
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
                num_analysis_samples = analysis_matrix.shape[1]
                if num_analysis_samples < 2:
                    st.warning("PCA preview requires at least 2 selected samples.")
                else:
                    if num_analysis_samples == 2:
                        st.warning(
                            "PCA preview with 2 samples should be interpreted as a simple distance-like overview."
                        )

                    pca_input = select_top_variable_features(
                        analysis_matrix,
                        top_n=int(top_variable_features),
                    )

                    pca_scores_df, explained = run_pca(
                        pca_input,
                        n_components=5,
                        scale=pca_scale,
                    )

                    pca_plot_df = build_pca_plot_df(
                        ds,
                        pca_scores_df,
                        explained_variance_ratio=explained,
                        use_exclude=use_exclude,
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
                        )

                    # Use Plotly for PCA as preferred before
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

    # --------------------------------------------------
    # 10. Sample Correlation
    # --------------------------------------------------
    st.header("10. Sample Correlation")

    if analysis_matrix is not None:
        corr_method = st.selectbox(
            "Correlation method",
            options=["pearson", "spearman"],
            index=0,
        )

        try:
            corr_df = compute_sample_correlation(
                analysis_matrix,
                method=corr_method,
            )

            st.write(
                f"**Correlation matrix shape:** `{corr_df.shape[0]}` × `{corr_df.shape[1]}`"
            )
            st.caption("Sample-to-sample correlation computed from the current analysis matrix.")

            st.subheader("Correlation Table")
            st.dataframe(format_display_df(corr_df), use_container_width=True)

            st.subheader("Correlation Heatmap")
            # Simple styled dataframe as a heatmap substitute
            st.dataframe(
                corr_df.style.background_gradient(axis=None),
                use_container_width=True,
            )

            with st.expander("Sample Annotation Table", expanded=False):
                ann_df = build_sample_annotation_table(ds, list(corr_df.columns))
                st.dataframe(format_display_df(ann_df), use_container_width=True)

        except Exception as e:
            st.error(f"Failed to compute sample correlation: {e}")

    # --------------------------------------------------
    # 11. Gene Search
    # --------------------------------------------------
    st.header("11. Gene Search")

    if analysis_matrix is not None:
        search_query = st.text_input("Search for Gene/Feature ID", placeholder="e.g. ACT1 or YAL001C")
        if search_query:
            hits = search_features(analysis_matrix.index, search_query)
            if not hits:
                st.info(f"No matches found for '{search_query}'")
            else:
                selected_gene = st.selectbox(f"Found {len(hits)} matches", options=hits)
                if selected_gene:
                    try:
                        profile_df = build_feature_profile_table(
                            ds,
                            selected_gene,
                            matrix_kind=matrix_kind,
                            log2p1=log2p1,
                            use_exclude=use_exclude,
                            min_feature_nonzero_samples=int(min_feature_nonzero_samples),
                            min_feature_mean=float(min_feature_mean),
                        )

                        st.subheader(f"Profile: {selected_gene}")
                        
                        # Simple bar chart for expression
                        st.bar_chart(profile_df, x="sample_id", y="expression_value", color="group" if "group" in profile_df.columns else None)

                        with st.expander("Show Profile Table", expanded=False):
                            st.dataframe(format_display_df(profile_df), use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to build profile for {selected_gene}: {e}")

    # --------------------------------------------------
    # 12. Top Variable Features
    # --------------------------------------------------
    st.header("12. Top Variable Features")

    if analysis_matrix is not None:
        top_n_stats = st.number_input("Show top N variable features", min_value=5, max_value=500, value=50, step=5)
        
        try:
            top_stats_df = get_top_variable_features(analysis_matrix, top_n=int(top_n_stats))
            st.write(f"Top {len(top_stats_df)} features by variance in the current analysis matrix.")
            st.dataframe(format_display_df(top_stats_df), use_container_width=True)
        except Exception as e:
            st.error(f"Failed to compute feature statistics: {e}")

    # --------------------------------------------------
    # 13. DEG Comparison Design
    # --------------------------------------------------
    st.header("13. DEG Comparison Design")

    if analysis_matrix is not None:
        comparison_sample_table = build_analysis_sample_table(
            ds,
            matrix_kind=matrix_kind,
            use_exclude=use_exclude,
        )

        comparison_candidate_columns = get_comparison_candidate_columns(comparison_sample_table)

        if not comparison_candidate_columns:
            st.info("No comparison-ready metadata columns were found.")
            deg_input_obj = None
        else:
            d1, d2, d3 = st.columns(3)
            with d1:
                comparison_column = st.selectbox(
                    "Comparison column",
                    options=comparison_candidate_columns,
                    index=0,
                )

            group_summary = summarize_groups(comparison_sample_table, comparison_column)
            valid_group_names = [
                str(g) for g in group_summary["group_name"].fillna("").astype(str).tolist()
                if str(g).strip() != ""
            ]

            if len(valid_group_names) < 2:
                st.warning("Selected comparison column does not have at least 2 non-empty groups.")
                deg_input_obj = None
            else:
                with d2:
                    group_a = st.selectbox(
                        "Group A",
                        options=valid_group_names,
                        index=0,
                    )

                remaining_groups = [g for g in valid_group_names if g != group_a]
                with d3:
                    group_b = st.selectbox(
                        "Group B",
                        options=remaining_groups,
                        index=0 if remaining_groups else None,
                    )

                st.subheader("Group Summary")
                st.dataframe(format_display_df(group_summary), use_container_width=True)

                try:
                    deg_input_obj = build_deg_input(
                        ds,
                        matrix_kind=matrix_kind,
                        group_column=comparison_column,
                        group_a=group_a,
                        group_b=group_b,
                        log2p1=log2p1,
                        use_exclude=use_exclude,
                        min_feature_nonzero_samples=int(min_feature_nonzero_samples),
                        min_feature_mean=float(min_feature_mean),
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
                            format_display_df(deg_input_obj.sample_table),
                            use_container_width=True,
                        )

                except Exception as e:
                    st.error(f"Failed to build comparison design: {e}")
                    deg_input_obj = None
    else:
        deg_input_obj = None

    # --------------------------------------------------
    # 14. DEG Preview Table
    # --------------------------------------------------
    st.header("14. DEG Preview Table")

    if deg_input_obj is not None:
        try:
            sort_options = ["abs_log2_fc", "log2_fc", "mean_group_a", "mean_group_b"]
            p1, p2 = st.columns(2)
            with p1:
                preview_sort_by = st.selectbox(
                    "Sort preview table by",
                    options=sort_options,
                    index=0,
                )
            with p2:
                preview_top_n = st.number_input(
                    "Rows to display",
                    min_value=10,
                    max_value=500,
                    value=50,
                    step=10,
                )

            deg_preview_df = build_deg_preview_table(
                deg_input_obj,
                sort_by=preview_sort_by,
                ascending=False,
            )

            preview_summary = summarize_deg_preview(deg_preview_df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Features", preview_summary["n_features"])
            c2.metric("Positive log2FC", preview_summary["n_positive_fc"])
            c3.metric("Negative log2FC", preview_summary["n_negative_fc"])
            c4.metric(
                "Max |log2FC|",
                f"{preview_summary['max_abs_log2_fc']:.3f}" if preview_summary["max_abs_log2_fc"] is not None else "NA",
            )

            st.caption(
                "Preview table only. Statistical testing (p-value / adjusted p-value) is not implemented yet. "
                "DEG Preview Table reflects the currently selected analysis matrix and transform settings."
            )

            st.dataframe(
                format_display_df(deg_preview_df.head(int(preview_top_n))),
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"Failed to build DEG preview table: {e}")
    else:
        st.info("Build a valid comparison design to preview DEG-like results.")
