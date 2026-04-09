import pytest
from unittest.mock import patch, MagicMock
from iwa_rnaseq_reporter.app.reporter_session_context import ReporterSessionContext
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import BundleDiagnostic

@pytest.fixture
def mock_session_state():
    state = {}
    with patch("streamlit.session_state", state):
        yield state

def test_sync_all_keys(mock_session_state):
    # Import from app inside the test to ensure streamlit is mocked
    from app import sync_reporter_session_state
    
    res_ctx = ResolvedInputContext(
        original_input_path="in",
        resolved_dataset_manifest_path="ds_path",
        resolved_bundle_manifest_path="bundle_path",
        input_kind="kind",
        load_mode="mode",
        resolution_messages=()
    )
    ds = MagicMock()
    bundle = MagicMock()
    diag = BundleDiagnostic(status="ok", user_message="ok")
    
    session_ctx = ReporterSessionContext(
        resolved_input_context=res_ctx,
        dataset=ds,
        analysis_bundle=bundle,
        analysis_bundle_diagnostic=diag
    )
    
    sync_reporter_session_state(session_ctx)
    
    assert mock_session_state["reporter_session_context"] == session_ctx
    assert mock_session_state["resolved_input_context"] == res_ctx
    assert mock_session_state["dataset"] == ds
    assert mock_session_state["analysis_bundle"] == bundle
    assert mock_session_state["analysis_bundle_diagnostic"] == diag

def test_sync_clears_stale_state(mock_session_state):
    from app import sync_reporter_session_state
    
    # Pre-fill with old data
    mock_session_state["analysis_bundle"] = MagicMock()
    mock_session_state["dataset"] = MagicMock()
    
    # New context with no bundle
    session_ctx = ReporterSessionContext(
        resolved_input_context=MagicMock(),
        dataset=None,
        analysis_bundle=None,
        analysis_bundle_diagnostic=None
    )
    
    sync_reporter_session_state(session_ctx)
    
    assert mock_session_state["analysis_bundle"] is None
    assert mock_session_state["dataset"] is None
    assert mock_session_state["reporter_session_context"] == session_ctx
