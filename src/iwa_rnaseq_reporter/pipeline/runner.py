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

logger = logging.getLogger(__name__)

def parse_bool(val: Any) -> bool:
    """Safely parse boolean from various types."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        s = val.lower().strip()
        if s in ("true", "1", "yes", "on", "t", "y"):
            return True
        if s in ("false", "0", "no", "off", "f", "n"):
            return False
    return bool(val)

def evaluate_criteria(metadata_rows: List[SampleMetadataRow], criteria: Dict[str, Any]) -> List[str]:
    """
    Evaluates criteria against list of SampleMetadataRow.
    Returns a list of specimen_id that match.
    """
    matched_ids = []
    for row in metadata_rows:
        if not row.include_flag:
            continue
            
        match = True
        for col, values in criteria.items():
            # Normalize single values to list
            if not isinstance(values, list):
                values = [values]
            
            attr_val = getattr(row, col, None)
            if attr_val is None:
                # Check in extra dict
                attr_val = row.extra.get(col)
                
            if attr_val is None:
                match = False
                break
            
            if str(attr_val) not in [str(v) for v in values]:
                match = False
                break
        
        if match:
            matched_ids.append(row.specimen_id)
            
    return matched_ids

def resolve_comparison(matrix_spec: MatrixSpec, comparison_spec: ComparisonSpec, dry_run: bool = False) -> tuple[ResolvedComparisonPlan, pd.DataFrame]:
    """
    Step 1: Resolver - Resolves Specs into an executable Plan.
    Also returns the matrix DataFrame.
    """
    # 1. Validate IDs
    if comparison_spec.input_matrix_id != matrix_spec.matrix_id:
        raise ValueError(
            f"ID Mismatch: ComparisonSpec expects {comparison_spec.input_matrix_id}, "
            f"but MatrixSpec is {matrix_spec.matrix_id}"
        )

    # 2. Sample Selector Enforcement
    selector = comparison_spec.sample_selector
    if selector.inclusion or selector.exclusion:
        # User requested NotImplementedError for non-empty selector to be honest about contract support
        raise NotImplementedError("ComparisonSpec.sample_selector (inclusion/exclusion) is not yet supported in v0.1.0.")

    # 3. Load Matrix
    matrix_path = Path(matrix_spec.matrix_path)
    if not matrix_path.exists():
        if dry_run:
            logger.warning(f"Dry-run: Matrix {matrix_path} not found. Using dummy data.")
            matrix_df = pd.DataFrame(index=["GENE1", "GENE2"], columns=["SPEC_0001", "SPEC_0002", "SPEC_0003", "SPEC_0004"], data=100)
        else:
            raise FileNotFoundError(f"Matrix file not found: {matrix_path}")
    else:
        matrix_df = pd.read_csv(matrix_path, sep="\t", index_col=0)

    # 4. Load Metadata
    metadata_path_str = matrix_spec.metadata.get("sample_metadata_path")
    if not metadata_path_str:
        raise ValueError("MatrixSpec.metadata.sample_metadata_path is missing.")
    
    metadata_path = Path(metadata_path_str)
    if not metadata_path.exists():
        if dry_run:
            logger.warning(f"Dry-run: Metadata {metadata_path} not found. Using dummy metadata.")
            metadata_df = pd.DataFrame({
                "specimen_id": ["SPEC_0001", "SPEC_0002", "SPEC_0003", "SPEC_0004"],
                "subject_id": ["SUBJ_0001", "SUBJ_0002", "SUBJ_0003", "SUBJ_0004"],
                "group_labels": ["case", "case", "control", "control"],
                "include_flag": [True, True, True, True]
            })
        else:
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    else:
        metadata_df = pd.read_csv(metadata_path)

    # Convert to SampleMetadataRow objects with safe parsing
    metadata_rows = []
    known_cols = {"specimen_id", "subject_id", "visit_id", "sample_name", "group_labels", "timepoint_label", "batch_label", "pairing_id", "include_flag", "note"}
    for _, r in metadata_df.iterrows():
        extra = {k: v for k, v in r.to_dict().items() if k not in known_cols}
        metadata_rows.append(SampleMetadataRow(
            specimen_id=str(r["specimen_id"]),
            subject_id=str(r["subject_id"]),
            visit_id=str(r.get("visit_id", "")) if not pd.isna(r.get("visit_id")) else None,
            sample_name=str(r.get("sample_name", "")) if not pd.isna(r.get("sample_name")) else None,
            group_labels=str(r.get("group_labels", "")) if not pd.isna(r.get("group_labels")) else None,
            timepoint_label=str(r.get("timepoint_label", "")) if not pd.isna(r.get("timepoint_label")) else None,
            batch_label=str(r.get("batch_label", "")) if not pd.isna(r.get("batch_label")) else None,
            pairing_id=str(r.get("pairing_id", "")) if not pd.isna(r.get("pairing_id")) else None,
            include_flag=parse_bool(r.get("include_flag", True)),
            note=str(r.get("note", "")) if not pd.isna(r.get("note")) else None,
            extra=extra
        ))

    # 5. Resolve Groups
    if len(comparison_spec.groups) < 2:
        raise ValueError("ComparisonSpec must have at least 2 groups.")
        
    group_a_spec = comparison_spec.groups[0]
    group_b_spec = comparison_spec.groups[1]
    
    group_a_ids = evaluate_criteria(metadata_rows, group_a_spec.criteria)
    group_b_ids = evaluate_criteria(metadata_rows, group_b_spec.criteria)
    
    # 6. Mismatch Logging
    all_metadata_ids = {r.specimen_id for r in metadata_rows if r.include_flag}
    all_matrix_ids = set(matrix_df.columns)
    
    missing_in_matrix = (set(group_a_ids) | set(group_b_ids)) - all_matrix_ids
    if missing_in_matrix:
        logger.warning(f"Specimens matched criteria but missing in matrix: {missing_in_matrix}")
        
    missing_in_metadata = all_matrix_ids - all_metadata_ids
    if missing_in_metadata:
        logger.warning(f"Specimens in matrix but missing/excluded in metadata: {missing_in_metadata}")

    # Map specimen IDs to subject IDs and filter by matrix columns
    group_a_valid = [s for s in group_a_ids if s in matrix_df.columns]
    group_b_valid = [s for s in group_b_ids if s in matrix_df.columns]
    
    # 7. Empty Group Validation
    if not group_a_valid:
        raise ValueError(f"Resolved group A '{group_a_spec.label}' is empty.")
    if not group_b_valid:
        raise ValueError(f"Resolved group B '{group_b_spec.label}' is empty.")

    subj_a = [r.subject_id for r in metadata_rows if r.specimen_id in group_a_valid]
    subj_b = [r.subject_id for r in metadata_rows if r.specimen_id in group_b_valid]

    # 8. Build Final Plan
    plan = ResolvedComparisonPlan(
        comparison_id=comparison_spec.comparison_id,
        input_matrix_id=matrix_spec.matrix_id,
        comparison_type=comparison_spec.comparison_type,
        analysis_intent=comparison_spec.analysis_intent or "differential_expression",
        group_a_label=group_a_spec.label,
        group_a_specimen_ids=group_a_valid,
        group_b_label=group_b_spec.label,
        group_b_specimen_ids=group_b_valid,
        paired=comparison_spec.paired,
        covariates=comparison_spec.covariates,
        group_a_subject_ids=subj_a,
        group_b_subject_ids=subj_b,
        group_a_matrix_columns=group_a_valid,
        group_b_matrix_columns=group_b_valid,
        sample_axis=matrix_spec.sample_axis,
        feature_type=matrix_spec.feature_type,
        normalization=matrix_spec.normalization,
        matrix_path=str(matrix_path),
        feature_annotation_path=matrix_spec.feature_annotation_path,
        sample_metadata_path=str(metadata_path),
        included_specimen_ids=group_a_valid + group_b_valid,
        excluded_specimen_ids=[r.specimen_id for r in metadata_rows if r.specimen_id not in (group_a_valid + group_b_valid)],
        metadata=comparison_spec.metadata
    )
    
    return plan, matrix_df

def run_analysis_engine(plan: ResolvedComparisonPlan, matrix_df: pd.DataFrame, tables_dir: Path) -> ResultSpec:
    """
    Step 2: Engine - Consumes the Plan and produces results.
    """
    logger.info(f"Executing Analysis: {plan.group_a_label} vs {plan.group_b_label}")
    
    # Prepare DEGInput
    deg_input = DEGInput(
        matrix_kind="count_matrix", 
        feature_matrix=matrix_df,
        group_column="comparison",
        group_a=plan.group_a_label,
        group_b=plan.group_b_label,
        group_a_samples=plan.group_a_specimen_ids,
        group_b_samples=plan.group_b_specimen_ids
    )
    
    deg_result = compute_statistical_deg(deg_input, method="welch_ttest", padj_method="fdr_bh")
    
    deg_out_path = tables_dir / "deg_results.tsv"
    deg_result.result_table.to_csv(deg_out_path, sep="\t", index=False)
    
    # Convert to ResultSpec
    result_rows = []
    for _, row in deg_result.result_table.iterrows():
        # Try to infer label if feature_id is actually a symbol or if there's a symbol col
        feat_id = str(row.get("feature_id", ""))
        feat_label = str(row.get("feature_label", feat_id)) # Falls back to ID
        
        result_rows.append(ResultRow(
            feature_id=feat_id,
            feature_label=feat_label,
            effect_size=float(row["log2_fc"]) if not pd.isna(row.get("log2_fc")) else None,
            effect_type="log2_fold_change",
            p_value=float(row["p_value"]) if not pd.isna(row.get("p_value")) else None,
            q_value=float(row["padj"]) if not pd.isna(row.get("padj")) else None,
            direction=str(row.get("direction", "")),
            base_mean=(float(row.get("mean_group_a", 0)) + float(row.get("mean_group_b", 0)))/2.0
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
        )
    )

def build_report_payload(plan: ResolvedComparisonPlan, result_spec: ResultSpec, dirs: Dict[str, Path]) -> ReportPayloadSpec:
    deg_out_path = dirs["tables"] / "deg_results.tsv"
    return ReportPayloadSpec(
        schema_name="ReportPayloadSpec",
        schema_version="0.1.0",
        report_payload_id=f"RP_{plan.comparison_id}",
        project_id="UNKNOWN",
        title=f"RNA-Seq DEG Report: {plan.group_a_label} vs {plan.group_b_label}",
        sections=[ReportSection("deg_table", "table", source_refs=[result_spec.result_id])],
        artifacts=[ReportArtifact("table", str(deg_out_path.resolve()))]
    )

def build_execution_run(plan: ResolvedComparisonPlan, result_spec: ResultSpec, payload_spec: ReportPayloadSpec, dirs: Dict[str, Path], started_at: str, dry_run: bool) -> ExecutionRunSpec:
    finished_at = datetime.now(timezone.utc).astimezone().isoformat()
    return ExecutionRunSpec(
        schema_name="ExecutionRunSpec",
        schema_version="0.1.0",
        run_id=f"RUN_{plan.comparison_id}",
        app_name="iwa_rnaseq_reporter",
        app_version="0.1.0",
        started_at=started_at,
        input_refs=[plan.input_matrix_id, plan.comparison_id],
        output_refs=[result_spec.result_id, payload_spec.report_payload_id],
        parameters={"dry_run": dry_run, "method": "welch_ttest"},
        execution_backend="local",
        finished_at=finished_at,
        status="completed", # Changed from "success" for consistency
        log_path=str((dirs["logs"] / "reporter.log").resolve())
    )

def run_reporter_pipeline(matrix_spec: MatrixSpec, comparison_spec: ComparisonSpec, outdir: Path, dry_run: bool = False) -> tuple[ResultSpec, ReportPayloadSpec, ExecutionRunSpec]:
    started_at = datetime.now(timezone.utc).astimezone().isoformat()
    
    # Prepare Output Directories
    outdir.mkdir(parents=True, exist_ok=True)
    dirs = {k: outdir / k for k in ["tables", "plots", "specs", "logs"]}
    for d in dirs.values(): d.mkdir(exist_ok=True)

    # 1. Resolve Comparison (Resolver)
    plan, matrix_df = resolve_comparison(matrix_spec, comparison_spec, dry_run=dry_run)
    
    # 2. Run Analysis (Engine)
    result_spec = run_analysis_engine(plan, matrix_df, dirs["tables"])

    # 3. Build Report Payload
    payload_spec = build_report_payload(plan, result_spec, dirs)
    
    # 4. Execution Run Records
    run_spec = build_execution_run(plan, result_spec, payload_spec, dirs, started_at, dry_run)
    
    return result_spec, payload_spec, run_spec
