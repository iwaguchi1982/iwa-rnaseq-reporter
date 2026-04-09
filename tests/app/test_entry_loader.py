import pytest
from unittest.mock import patch, MagicMock
from iwa_rnaseq_reporter.app.entry_loader import load_reporter_entry_state
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.app.reporter_session_context import ReporterSessionContext
from iwa_rnaseq_reporter.io.input_resolution import InputResolutionResult
from iwa_rnaseq_reporter.legacy.loader import ReporterLoadError

@pytest.fixture
def mock_resolution_success():
    return InputResolutionResult(
        original_input_path="/path/to/in",
        resolved_dataset_manifest_path="/path/to/dataset.json",
        resolved_bundle_manifest_path="/path/to/bundle.json",
        input_kind="dataset_dir",
        load_mode="dataset_plus_bundle",
        resolution_messages=["msg1"]
    )

@pytest.fixture
def mock_resolution_unresolved():
    return InputResolutionResult(
        original_input_path="/invalid",
        load_mode="unresolved",
        resolution_messages=["failed"]
    )

def test_load_entry_state_success(mock_resolution_success):
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle") as mock_load_bundle:
                
                mock_resolve.return_value = mock_resolution_success
                mock_ds = MagicMock()
                mock_load_ds.return_value = mock_ds
                mock_bundle = MagicMock()
                mock_bundle.warning_summary = None
                mock_bundle.sample_metadata_alignment_status = None
                mock_load_bundle.return_value = mock_bundle
                
                ctx = load_reporter_entry_state("/path/to/in")
                
                assert ctx.has_resolved_input is True
                assert ctx.has_dataset is True
                assert ctx.has_analysis_bundle is True
                assert ctx.analysis_bundle_diagnostic.status == "ok"
                assert ctx.dataset == mock_ds

def test_load_entry_state_unresolved(mock_resolution_unresolved):
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        mock_resolve.return_value = mock_resolution_unresolved
        
        ctx = load_reporter_entry_state("/invalid")
        
        assert ctx.has_resolved_input is True
        assert ctx.resolved_input_context.is_unresolved is True
        assert ctx.has_dataset is False

def test_load_entry_state_dataset_error(mock_resolution_success):
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            mock_resolve.return_value = mock_resolution_success
            mock_load_ds.side_effect = ReporterLoadError([])
            
            ctx = load_reporter_entry_state("/path/to/in")
            
            assert ctx.has_resolved_input is True
            assert ctx.has_dataset is False
            # Should still have resolved input context
            assert ctx.resolved_input_context.has_dataset_manifest is True

def test_load_entry_state_bundle_error(mock_resolution_success):
    with patch("iwa_rnaseq_reporter.app.entry_loader.resolve_reporter_input_paths") as mock_resolve:
        with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_dataset") as mock_load_ds:
            with patch("iwa_rnaseq_reporter.app.entry_loader.load_reporter_analysis_bundle") as mock_load_bundle:
                
                mock_resolve.return_value = mock_resolution_success
                mock_load_ds.return_value = MagicMock()
                mock_load_bundle.side_effect = Exception("bundle error")
                
                ctx = load_reporter_entry_state("/path/to/in")
                
                assert ctx.has_dataset is True
                assert ctx.has_analysis_bundle is False
                assert ctx.analysis_bundle_diagnostic.status == "error"
                assert "bundle error" in ctx.analysis_bundle_diagnostic.technical_message
