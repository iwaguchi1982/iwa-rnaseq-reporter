import pytest
from pathlib import Path
from iwa_rnaseq_reporter.models.report_payload import ReportPayloadSpec
from iwa_rnaseq_reporter.models.result import ResultSpec, ResultRow
from iwa_rnaseq_reporter.models.resolved_comparison import ResolvedComparisonPlan
from iwa_rnaseq_reporter.pipeline.report_payload_builder import (
    build_report_payload_spec,
    build_report_summary_snapshot
)

@pytest.fixture
def mock_dirs(tmp_path):
    dirs = {
        "tables": tmp_path / "tables",
        "plots": tmp_path / "plots",
        "specs": tmp_path / "specs",
        "logs": tmp_path / "logs"
    }
    for d in dirs.values():
        d.mkdir()
    return dirs

@pytest.fixture
def sample_plan():
    return ResolvedComparisonPlan(
        comparison_id="COMP_TEST_001",
        input_matrix_id="MAT_TEST_001",
        comparison_type="two_group",
        analysis_intent="discovery",
        group_a_label="Case",
        group_a_specimen_ids=["S1", "S2"],
        group_b_label="Control",
        group_b_specimen_ids=["S3", "S4"],
        group_a_matrix_columns=["S1", "S2"],
        group_b_matrix_columns=["S3", "S4"],
        normalization="log2_tpm",
        metadata={"comparison_column": "treatment", "matrix_kind": "tpm_matrix"}
    )

@pytest.fixture
def sample_result():
    rows = [
        ResultRow(feature_id="G1", effect_size=2.0, q_value=0.01),  # Sig Up
        ResultRow(feature_id="G2", effect_size=-1.5, q_value=0.04), # Sig Down
        ResultRow(feature_id="G3", effect_size=0.5, q_value=0.1),   # Not Sig
        ResultRow(feature_id="G4", effect_size=3.0, q_value=0.06),  # Not Sig (p > 0.05)
        ResultRow(feature_id="G5", effect_size=0.8, q_value=0.001), # Not Sig (fc < 1.0)
    ]
    return ResultSpec(
        schema_name="ResultSpec",
        schema_version="0.1.0",
        result_id="RES_TEST_001",
        comparison_id="COMP_TEST_001",
        result_kind="feature_level_statistics",
        feature_type="gene",
        rows=rows
    )

def test_build_report_payload_spec_basic(sample_plan, sample_result, mock_dirs):
    payload = build_report_payload_spec(
        sample_plan, 
        sample_result, 
        mock_dirs,
        padj_threshold=0.05,
        abs_log2_fc_threshold=1.0
    )
    
    assert isinstance(payload, ReportPayloadSpec)
    assert payload.report_payload_id == "RP_COMP_TEST_001"
    assert payload.identity.comparison_id == "COMP_TEST_001"
    assert payload.identity.group_a_label == "Case"
    assert payload.identity.group_b_label == "Control"
    
    # Check Summary
    assert payload.summary.n_features_tested == 5
    assert payload.summary.n_sig_up == 1   # G1
    assert payload.summary.n_sig_down == 1 # G2
    assert payload.summary.max_abs_log2_fc == 3.0 # G4
    
    # Check Display Context
    assert payload.display_context.padj_threshold == 0.05
    assert payload.display_context.abs_log2_fc_threshold == 1.0
    assert payload.display_context.matrix_kind == "tpm_matrix"
    
    # Check Narrative Slots
    assert len(payload.narrative_slots) == 2
    assert payload.narrative_slots[0].slot_key == "executive_summary"
    
    # Check Linkage
    assert len(payload.sections) == 2
    assert payload.sections[0].source_refs == ["RES_TEST_001"]

def test_build_report_summary_snapshot_no_thresholds(sample_result):
    summary = build_report_summary_snapshot(sample_result, padj_threshold=None, abs_log2_fc_threshold=None)
    
    assert summary.n_features_tested == 5
    assert summary.n_sig_up is None
    assert summary.n_sig_down is None
    assert summary.max_abs_log2_fc == 3.0

def test_payload_to_dict_serialization(sample_plan, sample_result, mock_dirs):
    payload = build_report_payload_spec(sample_plan, sample_result, mock_dirs)
    d = payload.to_dict()
    
    assert "$schema_name" in d
    assert "$schema_version" in d
    assert d["identity"]["comparison_id"] == "COMP_TEST_001"
    assert d["summary"]["n_sig_up"] == 1
    assert "narrative_slots" in d
    assert len(d["narrative_slots"]) == 2
