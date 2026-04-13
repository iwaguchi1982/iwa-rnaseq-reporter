import pytest
from iwa_rnaseq_reporter.models.comparison import ComparisonSpec, ComparisonGroup, SampleSelectorFilters
from iwa_rnaseq_reporter.models.matrix import MatrixSpec
from iwa_rnaseq_reporter.validation.validate_comparison_spec import validate_comparison_spec

def make_valid_comparison() -> ComparisonSpec:
    return ComparisonSpec(
        schema_name="ComparisonSpec",
        schema_version="0.1.0",
        comparison_id="COMP_0001",
        comparison_type="two_group",
        input_matrix_id="MAT_0100",
        groups=[
            ComparisonGroup(label="case", criteria={"group_labels": ["Treatment"]}),
            ComparisonGroup(label="control", criteria={"group_labels": ["Control"]}),
        ]
    )

def test_validate_comparison_spec_two_group_success():
    spec = make_valid_comparison()
    result = validate_comparison_spec(spec)
    assert result.is_valid
    assert result.error_count == 0

def test_validate_comparison_spec_duplicate_group_labels():
    spec = make_valid_comparison()
    spec.groups[0].label = "same"
    spec.groups[1].label = "same"
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "duplicate_group_label" for i in result.issues)

def test_validate_comparison_spec_empty_group_label():
    spec = make_valid_comparison()
    spec.groups[0].label = ""
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "empty_group_label" for i in result.issues)

def test_validate_comparison_spec_invalid_criteria_keys():
    spec = make_valid_comparison()
    spec.groups[0].criteria = {"unsupported_key": ["val"]}
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "unsupported_criteria_keys" for i in result.issues)

def test_validate_comparison_spec_unsupported_sample_selector():
    spec = make_valid_comparison()
    spec.sample_selector = SampleSelectorFilters(inclusion=[{"id": "S1"}])
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "unsupported_sample_selector" for i in result.issues)

def test_validate_comparison_spec_covariates_not_supported():
    spec = make_valid_comparison()
    spec.covariates = ["age"]
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "unsupported_covariates" for i in result.issues)

def test_validate_comparison_spec_paired_not_supported():
    spec = make_valid_comparison()
    spec.paired = True
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "unsupported_paired_analysis" for i in result.issues)

def test_validate_comparison_spec_input_matrix_mismatch():
    spec = make_valid_comparison()
    spec.input_matrix_id = "MAT_0100"
    
    matrix_spec = MatrixSpec(
        schema_name="MatrixSpec", schema_version="0.1.0",
        matrix_id="MAT_9999", # Mismatch
        matrix_scope="analysis", matrix_kind="count_matrix",
        feature_type="gene", value_type="integer", normalization="raw",
        feature_id_system="ensembl", sample_axis="specimen",
        matrix_path="m.tsv", source_assay_ids=[], source_specimen_ids=[], source_subject_ids=[],
        metadata={}, overlay={}
    )
    
    result = validate_comparison_spec(spec, matrix_spec=matrix_spec)
    assert not result.is_valid
    assert any(i.code == "matrix_id_mismatch" for i in result.issues)

def test_validate_comparison_spec_invalid_type_and_group_count():
    spec = make_valid_comparison()
    spec.comparison_type = "multi_group"
    spec.groups = [ComparisonGroup(label="g1")]
    result = validate_comparison_spec(spec)
    assert not result.is_valid
    assert any(i.code == "unsupported_comparison_type" for i in result.issues)
    assert any(i.code == "invalid_group_count" for i in result.issues)
