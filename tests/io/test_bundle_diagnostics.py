import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from iwa_rnaseq_reporter.io.input_resolution import InputResolutionResult

# Add project root and src to sys.path
root = Path(__file__).parent.parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "src"))

@patch("streamlit.session_state", {})
def test_diagnostics_ok():
    from app import sync_reporter_session_state
    from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
    
    # Mock bundle with no issues
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = None
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": True}
    
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle", return_value=mock_bundle):
                mock_resolve.return_value = InputResolutionResult(
                    original_input_path="/valid/path",
                    load_mode="dataset_plus_bundle",
                    resolved_dataset_manifest_path="ds",
                    resolved_bundle_manifest_path="bundle",
                    input_kind="kind",
                    resolution_messages=[]
                )
                mock_load_ds.return_value = MagicMock()
                
                ctx = load_reporter_entry_state("/valid/path")
                sync_reporter_session_state(ctx)
                
                import streamlit as st
                diag = st.session_state["analysis_bundle_diagnostic"]
                assert diag.status == "ok"
                assert "successfully" in diag.user_message

@patch("streamlit.session_state", {})
def test_diagnostics_warning_summary():
    from app import sync_reporter_session_state
    from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
    
    # Mock bundle with warnings
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = "Some warning"
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": True}
    
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle", return_value=mock_bundle):
                mock_resolve.return_value = InputResolutionResult(
                    original_input_path="/path/with/warning",
                    load_mode="dataset_plus_bundle",
                    resolved_dataset_manifest_path="ds",
                    resolved_bundle_manifest_path="bundle",
                    input_kind="kind",
                    resolution_messages=[]
                )
                mock_load_ds.return_value = MagicMock()
                
                ctx = load_reporter_entry_state("/path/with/warning")
                sync_reporter_session_state(ctx)
                
                import streamlit as st
                diag = st.session_state["analysis_bundle_diagnostic"]
                assert diag.status == "warning"
                assert "warnings" in diag.user_message.lower()
                assert "internal warnings" in diag.technical_message

@patch("streamlit.session_state", {})
def test_diagnostics_warning_alignment():
    from app import sync_reporter_session_state
    from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
    
    # Mock bundle with misalignment
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = None
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": False}
    
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle", return_value=mock_bundle):
                mock_resolve.return_value = InputResolutionResult(
                    original_input_path="/path/with/misalignment",
                    load_mode="dataset_plus_bundle",
                    resolved_dataset_manifest_path="ds",
                    resolved_bundle_manifest_path="bundle",
                    input_kind="kind",
                    resolution_messages=[]
                )
                mock_load_ds.return_value = MagicMock()
                
                ctx = load_reporter_entry_state("/path/with/misalignment")
                sync_reporter_session_state(ctx)
                
                import streamlit as st
                diag = st.session_state["analysis_bundle_diagnostic"]
                assert diag.status == "warning"
                assert "misaligned" in diag.technical_message

@patch("streamlit.session_state", {})
def test_diagnostics_error():
    from app import sync_reporter_session_state
    from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
    
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle", side_effect=Exception("Critical Failure")):
                mock_resolve.return_value = InputResolutionResult(
                    original_input_path="/broken/path",
                    load_mode="dataset_plus_bundle",
                    resolved_dataset_manifest_path="ds",
                    resolved_bundle_manifest_path="bundle",
                    input_kind="kind",
                    resolution_messages=[]
                )
                mock_load_ds.return_value = MagicMock()
                
                ctx = load_reporter_entry_state("/broken/path")
                sync_reporter_session_state(ctx)
                
                import streamlit as st
                diag = st.session_state["analysis_bundle_diagnostic"]
                assert diag.status == "error"
                assert "not available" in diag.user_message.lower()
                assert "Critical Failure" in diag.technical_message
