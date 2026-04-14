import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..models.matrix import MatrixSpec
from ..models.comparison import ComparisonSpec
from ..models.result import ResultSpec, ResultRow, ResultProvenance
from ..models.report_payload import ReportPayloadSpec, ReportSection, ReportArtifact
from ..models.execution_run import ExecutionRunSpec
from ..models.resolved_comparison import ResolvedComparisonPlan, SampleMetadataRow

# Import legacy analysis code from the now-internal legacy package
from ..legacy.deg_input import DEGInput
from ..legacy.deg_stats import compute_statistical_deg

from ..pipeline.comparison_resolver import resolve_comparison_plan
from ..validation.validate_comparison_spec import validate_comparison_spec

logger = logging.getLogger(__name__)

def load_matrix_dataframe(matrix_spec: MatrixSpec, dry_run: bool = False) -> pd.DataFrame:
    """
    Step 1: Load - Reads the matrix file or generates dummy data for dry-run.
    """
    matrix_path = Path(matrix_spec.matrix_path)
    if not matrix_path.exists():
        if dry_run:
            logger.warning(f"Dry-run: Matrix {matrix_path} not found. Using dummy data.")
            return pd.DataFrame(index=["GENE1", "GENE2"], columns=["SPEC_0001", "SPEC_0002", "SPEC_0003", "SPEC_0004"], data=100)
        else:
            raise FileNotFoundError(f"Matrix file not found: {matrix_path}")
    
    return pd.read_csv(matrix_path, sep="\t", index_col=0)

def run_analysis_engine(plan: ResolvedComparisonPlan, matrix_df: pd.DataFrame, tables_dir: Path) -> ResultSpec:
    """
    Step 3: Execute - Consumes the Resolved Plan and produces Results.
    TODO: In future, this could simply be run_analysis_engine(plan, matrix_df, ...)
    """
    logger.info(f"Executing Analysis: {plan.group_a_label} ({len(plan.group_a_matrix_columns)} samples) vs {plan.group_b_label} ({len(plan.group_b_matrix_columns)} samples)")
    
    # Prepare DEGInput (Legacy bridge)
    deg_input = DEGInput(
        matrix_kind="count_matrix", 
        feature_matrix=matrix_df,
        sample_table=pd.DataFrame({"sample_id": plan.group_a_matrix_columns + plan.group_b_matrix_columns}),
        group_column="comparison",
        group_a=plan.group_a_label,
        group_b=plan.group_b_label,
        group_a_samples=plan.group_a_matrix_columns,
        group_b_samples=plan.group_b_matrix_columns
    )
    
    deg_result = compute_statistical_deg(deg_input, method="welch_ttest", padj_method="fdr_bh")
    
    deg_out_path = tables_dir / "deg_results.tsv"
    deg_result.result_table.to_csv(deg_out_path, sep="\t", index=False)
    
    # Convert to ResultSpec
    result_rows = []
    for _, row in deg_result.result_table.iterrows():
        feat_id = str(row.get("feature_id", ""))
        feat_label = str(row.get("feature_label", feat_id))
        
        result_rows.append(ResultRow(
            feature_id=feat_id,
            feature_label=feat_label,
            effect_size=float(row["log2_fc"]) if not pd.isna(row.get("log2_fc")) else None,
            effect_type="log2_fold_change",
            p_value=float(row["p_value"]) if not pd.isna(row.get("p_value")) else None,
            q_value=float(row["padj"]) if not pd.isna(row.get("padj")) else None,
            direction=str(row.get("direction", "")),
            base_mean=(float(row.get("mean_group_a", 0)) + float(row.get("mean_group_b", 0)))/2.0,
            statistic=float(row["statistic"]) if not pd.isna(row.get("statistic")) else None,
            mean_group_a=float(row["mean_group_a"]) if not pd.isna(row.get("mean_group_a")) else None,
            mean_group_b=float(row["mean_group_b"]) if not pd.isna(row.get("mean_group_b")) else None
        ))
        
    return ResultSpec(
        schema_name="ResultSpec",
        schema_version="0.1.0",
        result_id=f"RES_{plan.comparison_id}",
        comparison_id=plan.comparison_id,
        result_kind="feature_level_statistics",
        feature_type=plan.feature_type,
        rows=result_rows,
        provenance=ResultProvenance(
            method="welch_ttest",
            method_version="0.1.0",
            parameters={
                "padj_method": "fdr_bh",
                "base_mean_definition": "mean(group_a_mean, group_b_mean)"
            }
        ),
        metadata={
            "group_a_label": plan.group_a_label,
            "group_b_label": plan.group_b_label,
            "feature_type": plan.feature_type,
            "normalization": plan.normalization
        }
    )

def build_report_payload(plan: ResolvedComparisonPlan, result_spec: ResultSpec, dirs: Dict[str, Path]) -> ReportPayloadSpec:
    """
    Step 4: Emit (Report) - Build display payload.
    """
    deg_out_path = dirs["tables"] / "deg_results.tsv"
    return ReportPayloadSpec(
        schema_name="ReportPayloadSpec",
        schema_version="0.1.0",
        report_payload_id=f"RP_{plan.comparison_id}",
        project_id="UNKNOWN",
        title=f"RNA-Seq DEG Report: {plan.group_a_label} vs {plan.group_b_label}",
        sections=[
            ReportSection("deg_table", "table", source_refs=[result_spec.result_id]),
            ReportSection("volcano_plot", "plot", source_refs=[result_spec.result_id]),
        ],
        artifacts=[ReportArtifact("table", str(deg_out_path.resolve()))],
        metadata={
            "group_a_label": plan.group_a_label,
            "group_b_label": plan.group_b_label,
            "group_a_size": len(plan.group_a_matrix_columns),
            "group_b_size": len(plan.group_b_matrix_columns),
        }
    )

def build_execution_run(plan: ResolvedComparisonPlan, result_spec: ResultSpec, payload_spec: ReportPayloadSpec, dirs: Dict[str, Path], started_at: str, dry_run: bool) -> ExecutionRunSpec:
    """
    Step 4: Emit (Provenance) - Record execution run.
    """
    finished_at = datetime.now(timezone.utc).astimezone().isoformat()
    return ExecutionRunSpec(
        schema_name="ExecutionRunSpec",
        schema_version="0.1.0",
        run_id=f"RUN_{plan.comparison_id}",
        app_name="iwa_rnaseq_reporter",
        app_version="0.3.5",
        started_at=started_at,
        input_refs=[plan.input_matrix_id, plan.comparison_id],
        output_refs=[result_spec.result_id, payload_spec.report_payload_id],
        parameters={"dry_run": dry_run, "method": "welch_ttest"},
        execution_backend="local",
        finished_at=finished_at,
        status="completed",
        log_path=str((dirs["logs"] / "reporter.log").resolve())
    )

def run_reporter_pipeline(matrix_spec: MatrixSpec, comparison_spec: ComparisonSpec, outdir: Path, dry_run: bool = False) -> tuple[ResultSpec, ReportPayloadSpec, ExecutionRunSpec]:
    """
    Main Orchestration Flow: load -> resolve -> execute -> emit
    """
    started_at = datetime.now(timezone.utc).astimezone().isoformat()
    
    # Prepare Output Directories
    # 0. Validate Comparison Spec (Lightweight Contract Check)
    v_result = validate_comparison_spec(comparison_spec, matrix_spec=matrix_spec)
    if not v_result.is_valid:
        errors = [i.message for i in v_result.issues if i.level == "error"]
        raise ValueError(f"ComparisonSpec validation failed: {v_result.summary()} Issues: {errors}")

    # Prepare Output Directories
    outdir.mkdir(parents=True, exist_ok=True)
    dirs = {k: outdir / k for k in ["tables", "plots", "specs", "logs"]}
    for d in dirs.values(): d.mkdir(exist_ok=True)

    # 1. Load Data
    matrix_df = load_matrix_dataframe(matrix_spec, dry_run=dry_run)
    
    # 2. Resolve Comparison (Strategy: delegate to comparison_resolver)
    resolved_plan = resolve_comparison_plan(
        matrix_spec=matrix_spec,
        comparison_spec=comparison_spec,
        matrix_df=matrix_df
    )
    
    # 3. Execute Analysis (Engine)
    result_spec = run_analysis_engine(resolved_plan, matrix_df, dirs["tables"])

    # 4. Emit Results (Report & Execution Records)
    payload_spec = build_report_payload(resolved_plan, result_spec, dirs)
    run_spec = build_execution_run(resolved_plan, result_spec, payload_spec, dirs, started_at, dry_run)
    
    return result_spec, payload_spec, run_spec
