import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root and src to sys.path
root = Path(__file__).parent.parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "src"))

# Mock streamlit before importing app.py components if possible
# Or just mock the components during the test.
@patch("streamlit.session_state", {})
def test_try_load_bundle_success():
    from app import _try_load_bundle
    
    mock_bundle = MagicMock()
    mock_bundle.warning_summary = None
    mock_bundle.sample_metadata_alignment_status = None
    
    with patch("app.load_reporter_analysis_bundle", return_value=mock_bundle):
        _try_load_bundle("/valid/path")
        
        import streamlit as st
        assert st.session_state["analysis_bundle"] == mock_bundle
        assert st.session_state["analysis_bundle_diagnostic"].status == "ok"

@patch("streamlit.session_state", {})
def test_try_load_bundle_failure():
    from app import _try_load_bundle
    
    with patch("app.load_reporter_analysis_bundle", side_effect=Exception("Load Failed")):
        _try_load_bundle("/invalid/path")
        
        import streamlit as st
        assert st.session_state["analysis_bundle"] is None
        assert st.session_state["analysis_bundle_diagnostic"].status == "error"
        assert st.session_state["analysis_bundle_diagnostic"].technical_message == "Load Failed"

if __name__ == "__main__":
    # Note: Running this might trigger app.py top-level execution if not careful.
    # In this app.py, st.set_page_config is called at top level.
    # We should probably run this with pytest and -s to see if it works.
    pass
