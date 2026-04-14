import pandas as pd
import pytest
from pathlib import Path
from iwa_rnaseq_reporter.models.resolved_comparison import ResolvedComparisonPlan
from iwa_rnaseq_reporter.pipeline.runner import run_analysis_engine
from iwa_rnaseq_reporter.models.result import ResultSpec

def test_run_analysis_engine_populates_extended_fields(tmp_path):
    # 1. Setup mock data
    # Gene 1: Up in B (A=1,1.1, B=10,10.1)
    # Gene 2: Down in B (A=10,10.1, B=1,1.1)
    matrix_df = pd.DataFrame({
        "A1": [1.0, 10.0],
        "A2": [1.1, 10.1],
        "B1": [10.0, 1.0],
        "B2": [10.1, 1.1],
    }, index=["G_UP", "G_DOWN"])
    
    plan = ResolvedComparisonPlan(
        comparison_id="COMP_001",
        input_matrix_id="MAT_001",
        comparison_type="two_group",
        analysis_intent="deg",
        group_a_label="Control",
        group_a_specimen_ids=["A1", "A2"],
        group_b_label="Case",
        group_b_specimen_ids=["B1", "B2"],
        group_a_matrix_columns=["A1", "A2"],
        group_b_matrix_columns=["B1", "B2"],
        feature_type="gene",
        normalization="tpm"
    )
    
    tables_dir = tmp_path / "tables"
    tables_dir.mkdir()
    
    # 2. Execute
    result_spec = run_analysis_engine(plan, matrix_df, tables_dir)
    
    # 3. Verify Spec
    assert isinstance(result_spec, ResultSpec)
    assert len(result_spec.rows) == 2
    
    # Check Rows
    up_row = next(r for r in result_spec.rows if r.feature_id == "G_UP")
    assert up_row.direction == "Up"
    assert up_row.p_value < 0.05
    
    # Verify extended fields are populated
    assert up_row.statistic is not None
    assert up_row.mean_group_a is not None
    assert up_row.mean_group_b is not None
    
    # Numerical validation (A means: 1.05, B means: 10.05)
    assert pytest.approx(up_row.mean_group_a) == 1.05
    assert pytest.approx(up_row.mean_group_b) == 10.05
    # base_mean should be the average of the two group means
    assert up_row.base_mean == (up_row.mean_group_a + up_row.mean_group_b) / 2.0

    # 4. Verify Metadata
    assert result_spec.metadata["group_a_label"] == "Control"
    assert result_spec.metadata["group_b_label"] == "Case"
    assert result_spec.metadata["feature_type"] == "gene"
    assert result_spec.metadata["normalization"] == "tpm"
    
    # 5. Verify Artifacts
    assert (tables_dir / "deg_results.tsv").exists()
