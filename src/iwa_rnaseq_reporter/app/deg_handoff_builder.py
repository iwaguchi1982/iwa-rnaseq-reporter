from typing import Optional
from iwa_rnaseq_reporter.app.deg_export_spec import DegExportPayload
from .deg_handoff_contract import (
    DegHandoffIdentitySpec,
    DegHandoffDataRefSpec,
    DegHandoffPayload,
    build_deg_comparison_id
)

def build_deg_handoff_payload(
    export_payload: DegExportPayload,
    bundle_filename: str,
    feature_id_system: Optional[str] = None
) -> DegHandoffPayload:
    """
    Build a formal handoff contract payload from an export payload.
    """
    summary = export_payload.summary
    metadata = export_payload.metadata
    metrics = export_payload.summary_metrics

    # 1. Identity
    comp_id = build_deg_comparison_id(
        summary.comparison_column,
        summary.group_a,
        summary.group_b,
        metadata.matrix_kind
    )
    identity = DegHandoffIdentitySpec(
        comparison_id=comp_id,
        comparison_label=summary.comparison_label,
        comparison_column=summary.comparison_column,
        group_a=summary.group_a,
        group_b=summary.group_b
    )

    # 2. Data Refs
    artifact_refs = DegHandoffDataRefSpec(
        bundle_filename=bundle_filename
    )

    # 3. Assemble
    return DegHandoffPayload(
        identity=identity,
        analysis_metadata=metadata.to_dict(),
        artifact_refs=artifact_refs,
        summary_metrics={
            "n_features_tested": metrics.n_features_tested,
            "n_sig_up": metrics.n_sig_up,
            "n_sig_down": metrics.n_sig_down,
            "max_abs_log2_fc": metrics.max_abs_log2_fc
        },
        feature_id_system=feature_id_system
    )
