import streamlit as st
import pandas as pd
from pathlib import Path
from src.loader import load_reporter_dataset, ReporterLoadError

st.set_page_config(page_title="iwa-rnaseq-reporter", layout="wide")

st.title("iwa-rnaseq-reporter")


def format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Polishes DataFrame for display by filling NAs and standardizing formats."""
    return df.fillna("-").replace("", "-")


def reorder_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reorders metadata columns for consistent display."""
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
    """Creates a DataFrame summarizing the status of all relevant files."""
    rows = []
    required_keys = ["sample_metadata", "sample_qc_summary", "gene_tpm", "gene_numreads", "run_summary"]
    optional_keys = ["transcript_tpm", "transcript_numreads", "sample_sheet", "run_config", "run_log"]

    for key in required_keys:
        path = ds.resolved_paths.get(key)
        rows.append({
            "file": key,
            "required": "yes",
            "status": "found" if path and path.exists() else "missing",
            "resolved_path": str(path) if path else "-"
        })
    for key in optional_keys:
        path = ds.resolved_paths.get(key)
        rows.append({
            "file": key,
            "required": "no",
            "status": "found" if path and path.exists() else "missing",
            "resolved_path": str(path) if path else "-"
        })
    return pd.DataFrame(rows)


def build_validation_df(ds) -> pd.DataFrame:
    """Creates a DataFrame for validation messages."""
    if not ds.messages:
        return pd.DataFrame(columns=["level", "code", "message"])
    return pd.DataFrame([
        {"level": m.level, "code": m.code, "message": m.message}
        for m in ds.messages
    ])


# 1. Input
st.header("1. Input")
input_path_str = st.text_input(
    "Dataset or Manifest Path", 
    placeholder="/path/to/run_dir or /path/to/results_dir or /path/to/dataset_manifest.json"
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

# 2. Status & Overview Sections
if "dataset" in st.session_state:
    ds = st.session_state["dataset"]
    
    # --- 2. Load Status ---
    st.header("2. Load Status")
    
    warning_count = sum(1 for m in ds.messages if m.level == "warning")
    info_count = sum(1 for m in ds.messages if m.level == "info")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Resolved Input Type:** `{ds.input_type}`")
    c2.write(f"**Required Files:** `{sum(1 for k in ds.resolved_paths if k in ['sample_metadata', 'sample_qc_summary', 'gene_tpm', 'gene_numreads', 'run_summary'] and ds.resolved_paths[k].exists())} / 5`")
    c3.write(f"**Optional Files:** `{sum(1 for k in ds.resolved_paths if k in ['transcript_tpm', 'transcript_numreads', 'sample_sheet', 'run_config', 'run_log'] and ds.resolved_paths[k].exists())} / 5`")
    c4.write(f"**Transcripts:** `{'available' if ds.transcript_tpm is not None else 'not available'}`")
    
    st.write(f"**Manifest Path:** `{ds.manifest_path}`")
    st.write(f"**Run Directory:** `{ds.base_dir}`")
    st.write(f"**Validation Warnings:** `{warning_count}` | **Info:** `{info_count}`")

    with st.expander("File Status Details", expanded=False):
        st.dataframe(build_file_status_df(ds), use_container_width=True)

    # --- 3. Dataset Overview ---
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

    # --- 4. Sample ID Summary ---
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
    
    # --- 5. Validation Messages ---
    st.header("5. Validation Messages")
    if ds.messages:
        fatal_count = sum(1 for m in ds.messages if m.level == "fatal")
        warning_count = sum(1 for m in ds.messages if m.level == "warning")
        info_count = sum(1 for m in ds.messages if m.level == "info")
        
        st.write(f"Fatal: `{fatal_count}` | Warning: `{warning_count}` | Info: `{info_count}`")
        st.dataframe(build_validation_df(ds), use_container_width=True)
        
        with st.expander("Message Details", expanded=ds.has_fatal or ds.has_warning):
            for msg in ds.messages:
                if msg.level == "fatal":
                    st.error(f"FATAL [{msg.code}]: {msg.message}")
                elif msg.level == "warning":
                    st.warning(f"WARNING [{msg.code}]: {msg.message}")
                else:
                    st.info(f"INFO [{msg.code}]: {msg.message}")
    else:
        st.success("No validation messages.")

    # --- 6. Sample Metadata ---
    st.header("6. Sample Metadata")
    display_metadata = reorder_metadata_columns(format_display_df(ds.sample_metadata.copy()))
    st.dataframe(display_metadata.head(10), use_container_width=True)
    
    # --- 7. Sample QC Summary ---
    st.header("7. Sample QC Summary")
    
    if "mapping_rate" in ds.sample_qc_summary.columns:
        # Convert to numeric to be safe
        mapping_series = pd.to_numeric(ds.sample_qc_summary["mapping_rate"], errors="coerce")
        q1, q2, q3 = st.columns(3)
        q1.metric("Avg Mapping Rate", f"{mapping_series.mean():.4f}" if mapping_series.notna().any() else "NA")
        q2.metric("Min Mapping Rate", f"{mapping_series.min():.4f}" if mapping_series.notna().any() else "NA")
        q3.metric("Max Mapping Rate", f"{mapping_series.max():.4f}" if mapping_series.notna().any() else "NA")
    
    if "qc_status" in ds.sample_qc_summary.columns:
        qc_counts = ds.sample_qc_summary["qc_status"].astype(str).value_counts(dropna=False)
        st.write("**QC Status Counts**")
        st.dataframe(qc_counts.rename_axis("qc_status").reset_index(name="count"), use_container_width=True)

    st.dataframe(format_display_df(ds.sample_qc_summary.head(10)), use_container_width=True)
