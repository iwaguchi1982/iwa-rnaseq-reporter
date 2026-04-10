import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from typing import Optional, Any

# Add src to sys.path to allow importing from iwa_rnaseq_reporter package
sys.path.append(str(Path(__file__).parent / "src"))

from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset, ReporterLoadError
from iwa_rnaseq_reporter.legacy.analysis import (
    get_matrix_by_kind,
)
from iwa_rnaseq_reporter.legacy.pca_utils import (
    run_pca,
)
from iwa_rnaseq_reporter.legacy.correlation_utils import (
    compute_sample_correlation,
)
from iwa_rnaseq_reporter.legacy.ui_utils import (
    format_display_df,
    get_nonempty_metadata_columns,
)
from iwa_rnaseq_reporter.legacy.gene_search import (
    search_features,
)
from iwa_rnaseq_reporter.legacy.feature_stats import (
    compute_feature_statistics,
)
from iwa_rnaseq_reporter.app.deg_sections import (
    render_deg_comparison_design_section,
    render_deg_analysis_section,
)
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle, BundleDiagnostic
from iwa_rnaseq_reporter.io.input_resolution import resolve_reporter_input_paths
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.app.reporter_session_context import ReporterSessionContext
from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
from iwa_rnaseq_reporter.app.analysis_config import AnalysisConfig, validate_analysis_config
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext
from iwa_rnaseq_reporter.app.analysis_workspace_builder import build_analysis_workspace
from iwa_rnaseq_reporter.app.analysis_sections import (
    render_analysis_matrix_summary,
    render_pca_preview_section,
    render_sample_correlation_section,
    render_gene_search_section,
    render_top_variable_features_section,
)
from iwa_rnaseq_reporter.app.comparison_portfolio_builder import build_empty_comparison_portfolio_context

st.set_page_config(page_title="iwa-rnaseq-reporter", layout="wide")
st.title("iwa-rnaseq-reporter")

# v0.16.1: Initialize comparison portfolio context
if "comparison_portfolio_context" not in st.session_state:
    st.session_state["comparison_portfolio_context"] = build_empty_comparison_portfolio_context()


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
    optional_keys = ["transcript_tpm", "transcript_numreads", "feature_annotation", "sample_sheet", "run_config", "run_log"]

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


def sync_reporter_session_state(session_ctx: ReporterSessionContext):
    """
    Sync the unified ReporterSessionContext with individual session_state keys 
    for downstream backward compatibility.
    """
    st.session_state["reporter_session_context"] = session_ctx
    
    # Sync legacy keys
    st.session_state["resolved_input_context"] = session_ctx.resolved_input_context
    st.session_state["dataset"] = session_ctx.dataset
    st.session_state["analysis_bundle"] = session_ctx.analysis_bundle
    st.session_state["analysis_bundle_diagnostic"] = session_ctx.analysis_bundle_diagnostic


def _render_bundle_summary(session_ctx: Optional[ReporterSessionContext]):
    """Render analysis bundle summary and diagnostics in Section 8."""
    if not session_ctx or not session_ctx.has_bundle_diagnostic:
        return

    diag = session_ctx.analysis_bundle_diagnostic
    
    # 1. Status Banner
    if diag.status == "ok":
        st.success(diag.user_message)
    elif diag.status == "warning":
        st.warning(diag.user_message)
    elif diag.status == "error":
        st.info(f"💡 {diag.user_message} (Dataset-only mode continues)")
    
    # 2. Handoff Summary (if available)
    bundle = session_ctx.analysis_bundle
    if bundle:
        st.markdown(f"**Target:** `{bundle.matrix_id}` (Run: `{bundle.run_id}`)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Run ID", bundle.run_id)
        c2.metric("Matrix ID", bundle.matrix_id)
        c3.metric("Sample Axis", bundle.sample_axis)
        
        s1, s2, s3 = st.columns(3)
        s1.write(f"**Shape:** `{bundle.matrix_shape['feature_count']}` features × `{bundle.matrix_shape['sample_count']}` samples")
        s2.write(f"**ID System:** `{bundle.feature_id_system}`")
        s3.write(f"**Producer:** `{bundle.producer}` (v`{bundle.producer_version}`)")
        
        # 3. Details Expander
        with st.expander("Technical Bundle Details", expanded=False):
            st.write("**Feature Annotation:**", bundle.feature_annotation_status if bundle.feature_annotation_status else "Not attached")
            st.write("**Sample Metadata Alignment:**", bundle.sample_metadata_alignment_status if bundle.sample_metadata_alignment_status else "Not verified")
            if diag.warning_flags:
                st.warning(f"**Diagnostic Warnings:** {', '.join(diag.warning_flags)}")
            if bundle.warning_summary:
                st.code(bundle.warning_summary, language="json")
            st.caption(f"Manifest Path: {bundle.analysis_bundle_manifest_path}")
    
    elif diag.status == "error":
        with st.expander("Diagnostic Error Details", expanded=False):
            st.write(f"**Error:** {diag.technical_message}")
            st.caption(f"Attempted Path: {diag.manifest_path}")


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
        try:
            # v0.13.4: Orchestrate entry load using specialized helper
            session_ctx = load_reporter_entry_state(input_path_str)
            sync_reporter_session_state(session_ctx)

            # Notification based on context
            res_ctx = session_ctx.resolved_input_context
            if res_ctx.is_unresolved:
                st.error("Failed to resolve input path.")
                for msg in res_ctx.resolution_messages:
                    st.info(msg)
            else:
                if not session_ctx.has_dataset:
                    st.warning("Dataset not loaded. Check resolution details.")
                
                st.success(f"Input resolved as {res_ctx.input_kind} ({res_ctx.load_mode})")
                
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

session_ctx = st.session_state.get("reporter_session_context")

if session_ctx and session_ctx.has_resolved_input:
    res_ctx = session_ctx.resolved_input_context
    with st.expander("Input Resolution Details", expanded=False):
        st.write(f"**Input Kind:** `{res_ctx.input_kind}`")
        st.write(f"**Load Mode:** `{res_ctx.load_mode}`")
        st.write(f"**Resolved Dataset:** `{res_ctx.resolved_dataset_manifest_path}`")
        st.write(f"**Resolved Bundle:** `{res_ctx.resolved_bundle_manifest_path}`")
        for msg in res_ctx.resolution_messages:
            st.caption(f"- {msg}")

if session_ctx and session_ctx.is_dataset_ready:
    ds = session_ctx.dataset

    # --------------------------------------------------
    # 2. Load Status
    # --------------------------------------------------
    st.header("2. Load Status")

    required_keys = ["sample_metadata", "sample_qc_summary", "gene_tpm", "gene_numreads", "run_summary"]
    optional_keys = ["transcript_tpm", "transcript_numreads", "feature_annotation", "sample_sheet", "run_config", "run_log"]

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
    
    # v0.12.3: Show bundle summary
    _render_bundle_summary(session_ctx)

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

    # v0.14.2a: Initialize downstream-dependent states to stabilize failure paths
    workspace: Optional[AnalysisWorkspaceContext] = None
    deg_input_obj: Optional[Any] = None
    comparison_column: Optional[str] = None
    group_a: Optional[str] = None
    group_b: Optional[str] = None

    # v0.14.1: Consolidate analysis configuration
    analysis_config = AnalysisConfig(
        matrix_kind=matrix_kind,
        log2p1=log2p1,
        use_exclude=use_exclude,
        min_feature_nonzero_samples=int(min_feature_nonzero_samples),
        min_feature_mean=float(min_feature_mean),
    )
    validate_analysis_config(analysis_config)

    try:
        # v0.14.3: Use builder for consolidated orchestration
        workspace = build_analysis_workspace(ds, analysis_config)

        # v0.14.4: Delegate display to section helper
        render_analysis_matrix_summary(workspace)

    except Exception as e:
        st.error(f"Failed to prepare analysis matrix: {e}")
        workspace = None

    # --------------------------------------------------
    # 9. PCA Preview
    # --------------------------------------------------
    if workspace is not None:
        render_pca_preview_section(workspace)

    # --------------------------------------------------
    # 10. Sample Correlation
    # --------------------------------------------------
    if workspace is not None:
        render_sample_correlation_section(workspace)

    # --------------------------------------------------
    # 11. Gene Search
    # --------------------------------------------------
    if workspace is not None:
        render_gene_search_section(workspace)

    # --------------------------------------------------
    # 12. Top Variable Features
    # --------------------------------------------------
    if workspace is not None:
        render_top_variable_features_section(workspace)

    # --------------------------------------------------
    # 13. DEG Comparison Design
    # --------------------------------------------------
    if workspace is not None:
        deg_input_obj, comparison_column, group_a, group_b = render_deg_comparison_design_section(workspace)
    else:
        deg_input_obj = None

    # --------------------------------------------------
    # 14. DEG Analysis (Statistical)
    # --------------------------------------------------
    render_deg_analysis_section(workspace, deg_input_obj, comparison_column, group_a, group_b)
