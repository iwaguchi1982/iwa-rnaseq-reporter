import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root and src to sys.path
root = Path(__file__).parent.parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "src"))

@patch("streamlit.session_state", {})
def test_diagnostics_ok():
    from app import _try_load_bundle
    
    # Mock bundle with no issues
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = None
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": True}
    
    with patch("app.load_reporter_analysis_bundle", return_value=mock_bundle):
        _try_load_bundle("/valid/path")
        
        import streamlit as st
        diag = st.session_state["analysis_bundle_diagnostic"]
        assert diag.status == "ok"
        assert "successfully" in diag.user_message

@patch("streamlit.session_state", {})
def test_diagnostics_warning_summary():
    from app import _try_load_bundle
    
    # Mock bundle with warnings
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = "Some warning"
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": True}
    
    with patch("app.load_reporter_analysis_bundle", return_value=mock_bundle):
        _try_load_bundle("/path/with/warning")
        
        import streamlit as st
        diag = st.session_state["analysis_bundle_diagnostic"]
        assert diag.status == "warning"
        assert "warnings" in diag.user_message.lower()
        assert "internal warnings" in diag.technical_message

@patch("streamlit.session_state", {})
def test_diagnostics_warning_alignment():
    from app import _try_load_bundle
    
    # Mock bundle with misalignment
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = None
    mock_bundle.sample_metadata_alignment_status = {"is_aligned": False}
    
    with patch("app.load_reporter_analysis_bundle", return_value=mock_bundle):
        _try_load_bundle("/path/with/misalignment")
        
        import streamlit as st
        diag = st.session_state["analysis_bundle_diagnostic"]
        assert diag.status == "warning"
        assert "misaligned" in diag.technical_message

@patch("streamlit.session_state", {})
def test_diagnostics_error():
    from app import _try_load_bundle
    
    with patch("app.load_reporter_analysis_bundle", side_effect=Exception("Critical Failure")):
        _try_load_bundle("/broken/path")
        
        import streamlit as st
        diag = st.session_state["analysis_bundle_diagnostic"]
        assert diag.status == "error"
        assert "not available" in diag.user_message.lower()
        assert "Critical Failure" in diag.technical_message

if __name__ == "__main__":
    pass
