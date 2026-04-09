import pytest
from iwa_rnaseq_reporter.app.reporter_session_context import ReporterSessionContext
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle, BundleDiagnostic

def test_empty_context():
    ctx = ReporterSessionContext()
    assert ctx.has_resolved_input is False
    assert ctx.has_dataset is False
    assert ctx.has_analysis_bundle is False
    assert ctx.has_bundle_diagnostic is False
    assert ctx.is_dataset_ready is False
    assert ctx.is_bundle_ready is False
    assert ctx.is_dataset_only_mode is False
    assert ctx.is_bundle_warning is False
    assert ctx.is_bundle_error is False

def test_dataset_ready_context():
    ctx = ReporterSessionContext(dataset=object())
    assert ctx.has_dataset is True
    assert ctx.is_dataset_ready is True
    assert ctx.is_dataset_only_mode is True
    assert ctx.is_bundle_ready is False

def test_bundle_ready_context():
    bundle = ReporterAnalysisBundle(
        run_id="run1", 
        matrix_id="mat1",
        analysis_bundle_manifest_path="path",
        contract_name="name",
        contract_version="v",
        bundle_kind="kind",
        producer="prod",
        producer_version="pv",
        matrix_shape={"feature_count": 10, "sample_count": 2},
        sample_axis="samples",
        feature_id_system="sys",
        column_order_specimen_ids=["s1", "s2"]
    )
    diag = BundleDiagnostic(status="ok", user_message="ok")
    
    ctx = ReporterSessionContext(analysis_bundle=bundle, analysis_bundle_diagnostic=diag)
    assert ctx.has_analysis_bundle is True
    assert ctx.has_bundle_diagnostic is True
    assert ctx.is_bundle_ready is True
    assert ctx.is_bundle_warning is False
    assert ctx.is_bundle_error is False

def test_bundle_warning_context():
    diag = BundleDiagnostic(status="warning", user_message="warning")
    ctx = ReporterSessionContext(analysis_bundle=object(), analysis_bundle_diagnostic=diag)
    assert ctx.is_bundle_ready is True
    assert ctx.is_bundle_warning is True
    assert ctx.is_bundle_error is False

def test_bundle_error_context():
    diag = BundleDiagnostic(status="error", user_message="error")
    ctx = ReporterSessionContext(analysis_bundle=None, analysis_bundle_diagnostic=diag)
    assert ctx.is_bundle_ready is False
    assert ctx.is_bundle_warning is False
    assert ctx.is_bundle_error is True

def test_from_parts():
    ctx = ReporterSessionContext.from_parts(dataset=object())
    assert ctx.has_dataset is True

def test_update():
    ctx = ReporterSessionContext(dataset=object())
    bundle = object()
    new_ctx = ctx.update(analysis_bundle=bundle)
    
    assert ctx.analysis_bundle is None
    assert new_ctx.dataset == ctx.dataset
    assert new_ctx.analysis_bundle == bundle
