import pytest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

# Dynamic path resolution to avoid absolute path dependency
THIS_FILE = Path(__file__).resolve()
REPORTER_ROOT = THIS_FILE.parents[2]  # tests/integration -> tests -> reporter_root
ORCHESTRA_ROOT = REPORTER_ROOT.parent # iwa_bio_analysis_orchestra

# Fixture paths from iwa_rnaseq_counter
COUNTER_FIXTURES_ROOT = ORCHESTRA_ROOT / "iwa_rnaseq_counter/tests/fixtures/analysis_bundle"
if not COUNTER_FIXTURES_ROOT.exists():
    raise RuntimeError(f"Counter fixtures not found (expected at {COUNTER_FIXTURES_ROOT}). "
                       "Ensure sister repo iwa-rnaseq-counter is present.")

MINIMAL_BUNDLE_MANIFEST = COUNTER_FIXTURES_ROOT / "valid_minimal_bundle/results/analysis_bundle_manifest.json"
WARNING_BUNDLE_MANIFEST = COUNTER_FIXTURES_ROOT / "valid_with_warnings/results/analysis_bundle_manifest.json"

# Add project src and app root to sys.path
REPORTER_ROOT = ORCHESTRA_ROOT / "iwa_rnaseq_reporter"
sys.path.append(str(REPORTER_ROOT / "src"))
sys.path.append(str(REPORTER_ROOT))

# Imports from reporter
from iwa_rnaseq_reporter.io.bundle_loader import load_reporter_analysis_bundle
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle

def test_integration_minimal_bundle_loading():
    """
    Verify that a minimal valid bundle from Counter is correctly ingested.
    """
    assert MINIMAL_BUNDLE_MANIFEST.exists(), f"Fixture not found at {MINIMAL_BUNDLE_MANIFEST}"
    
    bundle_view = load_reporter_analysis_bundle(str(MINIMAL_BUNDLE_MANIFEST))
    
    # Verify required handoff fields (Source of truth: v0.12_REPORTER_HANDOFF_PROFILE.md)
    assert isinstance(bundle_view, ReporterAnalysisBundle)
    assert bundle_view.run_id is not None
    assert bundle_view.matrix_id is not None
    assert "feature_count" in bundle_view.matrix_shape
    assert "sample_count" in bundle_view.matrix_shape
    assert bundle_view.sample_axis in ["columns", "rows", "specimen"]
    assert bundle_view.feature_id_system is not None
    assert isinstance(bundle_view.column_order_specimen_ids, list)
    assert str(bundle_view.analysis_bundle_manifest_path) == str(MINIMAL_BUNDLE_MANIFEST.resolve())

@patch("streamlit.session_state", {})
def test_integration_diagnostic_warning():
    """
    Verify that a bundle with internal warnings is diagnosed correctly in the app logic.
    """
    assert WARNING_BUNDLE_MANIFEST.exists(), f"Fixture not found at {WARNING_BUNDLE_MANIFEST}"
    
    from app import _try_load_bundle
    import streamlit as st
    
    # Execute the app logic
    _try_load_bundle(str(WARNING_BUNDLE_MANIFEST))
    
    diag = st.session_state["analysis_bundle_diagnostic"]
    assert diag.status == "warning"
    assert any("internal warnings" in f.lower() or "internal warnings" in diag.technical_message.lower() for f in diag.warning_flags) or "Warnings detected" in diag.technical_message
    
    # Ensure the bundle itself was still loaded
    assert st.session_state["analysis_bundle"] is not None
    assert st.session_state["analysis_bundle"].matrix_id is not None

@patch("streamlit.session_state", {})
def test_integration_non_fatal_fallback():
    """
    Verify that an invalid path results in an error diagnostic but remains non-fatal.
    """
    from app import _try_load_bundle
    import streamlit as st
    
    invalid_path = "/tmp/non_existent_bundle_manifest.json"
    
    # Execute the app logic
    _try_load_bundle(invalid_path)
    
    diag = st.session_state["analysis_bundle_diagnostic"]
    assert diag.status == "error"
    assert "not available" in diag.user_message.lower()
    assert st.session_state["analysis_bundle"] is None

if __name__ == "__main__":
    pass
