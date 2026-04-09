import pytest
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.io.input_resolution import InputResolutionResult

def test_context_from_result():
    res = InputResolutionResult(
        original_input_path="/path/to/in",
        resolved_dataset_manifest_path="/path/to/dataset.json",
        resolved_bundle_manifest_path="/path/to/bundle.json",
        input_kind="dataset_dir",
        load_mode="dataset_plus_bundle",
        resolution_messages=["msg1", "msg2"]
    )
    
    ctx = ResolvedInputContext.from_resolution_result(res)
    
    assert ctx.original_input_path == "/path/to/in"
    assert ctx.resolved_dataset_manifest_path == "/path/to/dataset.json"
    assert ctx.resolved_bundle_manifest_path == "/path/to/bundle.json"
    assert ctx.input_kind == "dataset_dir"
    assert ctx.load_mode == "dataset_plus_bundle"
    assert ctx.resolution_messages == ("msg1", "msg2")
    
    # Properties
    assert ctx.has_dataset_manifest is True
    assert ctx.has_bundle_manifest is True
    assert ctx.is_unresolved is False

def test_context_unresolved():
    res = InputResolutionResult(
        original_input_path="/invalid",
        load_mode="unresolved",
        resolution_messages=["failed"]
    )
    
    ctx = ResolvedInputContext.from_resolution_result(res)
    assert ctx.is_unresolved is True
    assert ctx.has_dataset_manifest is False
    assert ctx.has_bundle_manifest is False

def test_to_display_dict():
    ctx = ResolvedInputContext(
        original_input_path="in",
        resolved_dataset_manifest_path="ds",
        resolved_bundle_manifest_path=None,
        input_kind="kind",
        load_mode="mode",
        resolution_messages=()
    )
    
    d = ctx.to_display_dict()
    assert d["Original Input"] == "in"
    assert d["Dataset Manifest"] == "ds"
    assert d["Bundle Manifest"] == "None"
