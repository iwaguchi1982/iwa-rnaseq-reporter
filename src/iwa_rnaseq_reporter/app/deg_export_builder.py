from typing import Any, Optional
from iwa_rnaseq_reporter.app.deg_result_context import DegResultContext
from .deg_export_spec import (
    DegExportSummarySpec,
    DegExportRunMetadataSpec,
    DegExportPayload
)

def build_deg_export_payload(
    context: DegResultContext,
    deg_input_obj: Optional[Any] = None
) -> DegExportPayload:
    """
    Transform an internal result context into an external export payload.
    """
    # 1. Build Summary Spec
    # If deg_input_obj is provided, we can get actual group sample counts.
    # Otherwise, fallback (though context should ideally have this in v0.16)
    n_a = 0
    n_b = 0
    if deg_input_obj is not None:
        n_a = len(getattr(deg_input_obj, "group_a_samples", []))
        n_b = len(getattr(deg_input_obj, "group_b_samples", []))

    summary_spec = DegExportSummarySpec(
        comparison_column=context.comparison_column,
        group_a=context.group_a,
        group_b=context.group_b,
        comparison_label=context.comparison_label,
        sample_count_group_a=n_a,
        sample_count_group_b=n_b
    )

    # 2. Build Run Metadata Spec
    metadata_spec = DegExportRunMetadataSpec(
        matrix_kind=context.matrix_kind,
        log2p1=context.analysis_config_snapshot.log2p1,
        use_exclude=context.analysis_config_snapshot.use_exclude,
        min_feature_nonzero_samples=context.analysis_config_snapshot.min_feature_nonzero_samples,
        min_feature_mean=context.analysis_config_snapshot.min_feature_mean,
        padj_threshold=context.threshold_snapshot.padj_threshold,
        abs_log2_fc_threshold=context.threshold_snapshot.abs_log2_fc_threshold,
        sort_by=context.threshold_snapshot.sort_by,
        preview_top_n=context.threshold_snapshot.preview_top_n
    )

    # 3. Assemble Payload
    return DegExportPayload(
        summary=summary_spec,
        metadata=metadata_spec,
        result_table=context.result_table,
        summary_metrics=context.summary_metrics
    )
