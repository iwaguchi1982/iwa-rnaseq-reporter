import json
from pathlib import Path
from iwa_rnaseq_reporter.models.result import ResultSpec, ResultRow
from iwa_rnaseq_reporter.models.resolved_comparison import ResolvedComparisonPlan
from iwa_rnaseq_reporter.pipeline.report_payload_builder import build_report_payload_spec

def verify_json():
    plan = ResolvedComparisonPlan(
        comparison_id="CONF_CHECK_001",
        input_matrix_id="MAT_001",
        comparison_type="two_group",
        analysis_intent="clinical",
        group_a_label="Tumor",
        group_a_specimen_ids=["T1"],
        group_b_label="Normal",
        group_b_specimen_ids=["N1"],
        group_a_matrix_columns=["T1"],
        group_b_matrix_columns=["N1"],
        normalization="raw",
        metadata={"comparison_column": "sample_type", "matrix_kind": "count_matrix"}
    )
    
    rows = [
        ResultRow(feature_id="FEN1", effect_size=3.4, q_value=0.0001),
        ResultRow(feature_id="GAPDH", effect_size=0.1, q_value=0.5),
    ]
    result = ResultSpec(
        schema_name="ResultSpec", schema_version="0.1.0",
        result_id="RES_001", comparison_id="CONF_CHECK_001",
        result_kind="feature_level_statistics", feature_type="gene",
        rows=rows
    )
    
    dirs = {k: Path(f"/tmp/{k}") for k in ["tables", "plots", "specs", "logs"]}
    for d in dirs.values(): d.mkdir(parents=True, exist_ok=True)
    
    payload = build_report_payload_spec(plan, result, dirs, padj_threshold=0.05, abs_log2_fc_threshold=1.0)
    
    output_path = Path("iwa_rnaseq_reporter/run_results/verification_report_payload.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(payload.to_dict(), f, indent=2)
    
    print(f"Generated verification payload at {output_path}")

if __name__ == "__main__":
    verify_json()
