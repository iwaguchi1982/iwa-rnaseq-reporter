from typing import List, Optional, Dict, Any
from pathlib import Path
from ..models.report_payload import (
    ReportPayloadSpec, 
    ReportSection, 
    ReportArtifact,
    ReportIdentitySpec,
    ReportSummarySnapshot,
    ReportDisplayContextSnapshot,
    ReportNarrativeSlot
)
from ..models.result import ResultSpec
from ..models.resolved_comparison import ResolvedComparisonPlan

def build_report_identity(plan: ResolvedComparisonPlan) -> ReportIdentitySpec:
    """
    Assemble the identity spectrum for the report.
    """
    return ReportIdentitySpec(
        comparison_id=plan.comparison_id,
        comparison_label=f"{plan.group_a_label} vs {plan.group_b_label}",
        comparison_column=plan.metadata.get("comparison_column"),
        group_a_label=plan.group_a_label,
        group_b_label=plan.group_b_label,
        sample_count_group_a=len(plan.group_a_matrix_columns),
        sample_count_group_b=len(plan.group_b_matrix_columns)
    )

def build_report_summary_snapshot(
    result_spec: ResultSpec, 
    padj_threshold: Optional[float] = None, 
    abs_log2_fc_threshold: Optional[float] = None
) -> ReportSummarySnapshot:
    """
    Calculate high-level summary metrics from the statistical core.
    """
    n_features_tested = len(result_spec.rows)
    n_sig_up = None
    n_sig_down = None
    max_abs_log2_fc = None
    
    if n_features_tested > 0:
        abs_fcs = [abs(r.effect_size) for r in result_spec.rows if r.effect_size is not None]
        if abs_fcs:
            max_abs_log2_fc = max(abs_fcs)
            
    # n_sig counts are ONLY populated if both thresholds are provided
    if padj_threshold is not None and abs_log2_fc_threshold is not None:
        n_sig_up = 0
        n_sig_down = 0
        for r in result_spec.rows:
            if r.q_value is not None and r.q_value < padj_threshold:
                if r.effect_size is not None:
                    if r.effect_size > abs_log2_fc_threshold:
                        n_sig_up += 1
                    elif r.effect_size < -abs_log2_fc_threshold:
                        n_sig_down += 1
                        
    return ReportSummarySnapshot(
        n_features_tested=n_features_tested,
        n_sig_up=n_sig_up,
        n_sig_down=n_sig_down,
        max_abs_log2_fc=max_abs_log2_fc
    )

def build_report_display_context_snapshot(
    plan: ResolvedComparisonPlan,
    padj_threshold: Optional[float] = None,
    abs_log2_fc_threshold: Optional[float] = None,
    sort_by: Optional[str] = None,
    preview_top_n: Optional[int] = None
) -> ReportDisplayContextSnapshot:
    """
    Capture the threshold and display settings used to generate the report.
    """
    return ReportDisplayContextSnapshot(
        padj_threshold=padj_threshold,
        abs_log2_fc_threshold=abs_log2_fc_threshold,
        sort_by=sort_by,
        preview_top_n=preview_top_n,
        matrix_kind=plan.metadata.get("matrix_kind"),
        normalization=plan.normalization
    )

def build_default_narrative_slots(result_spec: ResultSpec) -> List[ReportNarrativeSlot]:
    """
    Initialize the skeleton for human or AI text commentary.
    Linked to the result_spec via source_refs.
    """
    return [
        ReportNarrativeSlot(
            slot_key="executive_summary", 
            title="Executive Summary",
            text=None,
            source_refs=[result_spec.result_id]
        ),
        ReportNarrativeSlot(
            slot_key="interpretation", 
            title="Biological Interpretation",
            text=None,
            source_refs=[result_spec.result_id]
        )
    ]

def build_report_payload_spec(
    plan: ResolvedComparisonPlan, 
    result_spec: ResultSpec, 
    dirs: Dict[str, Path],
    padj_threshold: Optional[float] = None,
    abs_log2_fc_threshold: Optional[float] = None,
    sort_by: Optional[str] = None,
    preview_top_n: Optional[int] = None
) -> ReportPayloadSpec:
    """
    Main entry point for assembling the ReportPayloadSpec.
    This builder consolidates common truth for UI, Export, and Summary.
    
    NOTE: Unlike earlier versions, we do not hardcode default thresholds here.
    The Truth must be passed explicitly from the orchestration layer.
    """
    identity = build_report_identity(plan)
    summary = build_report_summary_snapshot(result_spec, padj_threshold, abs_log2_fc_threshold)
    display_context = build_report_display_context_snapshot(
        plan, padj_threshold, abs_log2_fc_threshold, sort_by, preview_top_n
    )
    narrative_slots = build_default_narrative_slots(result_spec)
    
    deg_out_path = dirs["tables"] / "deg_results.tsv"
    
    return ReportPayloadSpec(
        schema_name="ReportPayloadSpec",
        schema_version="0.2.1",
        report_payload_id=f"RP_{plan.comparison_id}",
        project_id="UNKNOWN",
        title=f"RNA-Seq DEG Report: {plan.group_a_label} vs {plan.group_b_label}",
        identity=identity,
        summary=summary,
        display_context=display_context,
        narrative_slots=narrative_slots,
        sections=[
            ReportSection("deg_table", "table", source_refs=[result_spec.result_id]),
            ReportSection("volcano_plot", "plot", source_refs=[result_spec.result_id]),
        ],
        artifacts=[
            ReportArtifact("table", str(deg_out_path.resolve())),
        ],
        metadata={
            "app_version": "0.4.1",
            "feature_type": plan.feature_type
        }
    )
