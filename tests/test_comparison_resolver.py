from __future__ import annotations

import pandas as pd
import pytest

from iwa_rnaseq_reporter.models.matrix import MatrixSpec
from iwa_rnaseq_reporter.models.comparison import (
    ComparisonSpec,
    ComparisonGroup,
    SampleSelectorFilters,
)
from iwa_rnaseq_reporter.pipeline.comparison_resolver import resolve_comparison_plan


def write_sample_metadata_csv(tmp_path, content: str):
    path = tmp_path / "sample_metadata.csv"
    path.write_text(content, encoding="utf-8")
    return path


def make_matrix_spec(sample_metadata_path: str) -> MatrixSpec:
    return MatrixSpec(
        schema_name="MatrixSpec",
        schema_version="0.1.0",
        matrix_id="MAT_0100",
        matrix_scope="analysis",
        matrix_kind="count_matrix",
        feature_type="gene",
        value_type="integer",
        normalization="raw",
        feature_id_system="ensembl_gene_id",
        sample_axis="specimen",
        matrix_path="/tmp/merged_gene_numreads.tsv",
        feature_annotation_path="",
        source_assay_ids=["ASSAY_0001", "ASSAY_0002", "ASSAY_0003", "ASSAY_0004"],
        source_specimen_ids=["SPEC_0001", "SPEC_0002", "SPEC_0003", "SPEC_0004"],
        source_subject_ids=["SUBJ_0001", "SUBJ_0002", "SUBJ_0003", "SUBJ_0004"],
        metadata={
            "sample_metadata_path": str(sample_metadata_path),
        },
        overlay={},
    )


def make_two_group_comparison() -> ComparisonSpec:
    return ComparisonSpec(
        schema_name="ComparisonSpec",
        schema_version="0.1.0",
        comparison_id="COMP_0001",
        comparison_type="two_group",
        input_matrix_id="MAT_0100",
        sample_selector=SampleSelectorFilters(inclusion=[], exclusion=[]),
        groups=[
            ComparisonGroup(
                label="group_a",
                criteria={"group_labels": ["case"]},
            ),
            ComparisonGroup(
                label="group_b",
                criteria={"group_labels": ["control"]},
            ),
        ],
        paired=False,
        covariates=[],
        analysis_intent="differential_expression",
        metadata={},
        overlay={},
    )


def make_matrix_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SPEC_0001": [10, 20, 30],
            "SPEC_0002": [11, 19, 29],
            "SPEC_0003": [40, 50, 60],
            "SPEC_0004": [41, 49, 59],
        },
        index=["GENE_1", "GENE_2", "GENE_3"],
    )


def test_resolve_comparison_plan_two_group_success(tmp_path):
    sample_metadata_path = write_sample_metadata_csv(
        tmp_path,
        """specimen_id,subject_id,visit_id,sample_name,group_labels,timepoint_label,batch_label,pairing_id,include_flag,note
SPEC_0001,SUBJ_0001,VISIT_0001,sample01,case,baseline,batch1,,true,
SPEC_0002,SUBJ_0002,VISIT_0001,sample02,case,baseline,batch1,,true,
SPEC_0003,SUBJ_0003,VISIT_0001,sample03,control,baseline,batch2,,true,
SPEC_0004,SUBJ_0004,VISIT_0001,sample04,control,baseline,batch2,,true,
""",
    )

    matrix_spec = make_matrix_spec(sample_metadata_path)
    comparison_spec = make_two_group_comparison()
    matrix_df = make_matrix_df()

    plan = resolve_comparison_plan(
        matrix_spec=matrix_spec,
        comparison_spec=comparison_spec,
        matrix_df=matrix_df,
    )

    assert plan.comparison_id == "COMP_0001"
    assert plan.input_matrix_id == "MAT_0100"
    assert plan.group_a_label == "group_a"
    assert plan.group_b_label == "group_b"
    assert plan.group_a_specimen_ids == ["SPEC_0001", "SPEC_0002"]
    assert plan.group_b_specimen_ids == ["SPEC_0003", "SPEC_0004"]
    assert plan.group_a_matrix_columns == ["SPEC_0001", "SPEC_0002"]
    assert plan.group_b_matrix_columns == ["SPEC_0003", "SPEC_0004"]
    assert plan.included_specimen_ids == ["SPEC_0001", "SPEC_0002", "SPEC_0003", "SPEC_0004"]
    assert plan.excluded_specimen_ids == []


def test_resolve_comparison_plan_unknown_criteria_key_raises(tmp_path):
    sample_metadata_path = write_sample_metadata_csv(
        tmp_path,
        """specimen_id,subject_id,group_labels
SPEC_0001,SUBJ_0001,case
SPEC_0002,SUBJ_0002,control
""",
    )

    matrix_spec = make_matrix_spec(sample_metadata_path)
    matrix_df = pd.DataFrame(
        {
            "SPEC_0001": [1, 2],
            "SPEC_0002": [3, 4],
        },
        index=["GENE_1", "GENE_2"],
    )

    comparison_spec = ComparisonSpec(
        schema_name="ComparisonSpec",
        schema_version="0.1.0",
        comparison_id="COMP_0002",
        comparison_type="two_group",
        input_matrix_id="MAT_0100",
        sample_selector=SampleSelectorFilters(inclusion=[], exclusion=[]),
        groups=[
            ComparisonGroup(label="group_a", criteria={"unknown_key": ["x"]}),
            ComparisonGroup(label="group_b", criteria={"group_labels": ["control"]}),
        ],
        paired=False,
        covariates=[],
        analysis_intent="differential_expression",
        metadata={},
        overlay={},
    )

    with pytest.raises(NotImplementedError, match="Unsupported criteria keys"):
        resolve_comparison_plan(
            matrix_spec=matrix_spec,
            comparison_spec=comparison_spec,
            matrix_df=matrix_df,
        )


def test_resolve_comparison_plan_missing_matrix_column_raises(tmp_path):
    sample_metadata_path = write_sample_metadata_csv(
        tmp_path,
        """specimen_id,subject_id,group_labels
SPEC_0001,SUBJ_0001,case
SPEC_9999,SUBJ_9999,control
""",
    )

    matrix_spec = make_matrix_spec(sample_metadata_path)
    matrix_df = pd.DataFrame(
        {
            "SPEC_0001": [1, 2],
            "SPEC_0002": [3, 4],
        },
        index=["GENE1", "GENE2"],
    )

    comparison_spec = make_two_group_comparison()

    with pytest.raises(ValueError, match="not found in matrix columns"):
        resolve_comparison_plan(
            matrix_spec=matrix_spec,
            comparison_spec=comparison_spec,
            matrix_df=matrix_df,
        )
