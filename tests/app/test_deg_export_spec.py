import pytest
import pandas as pd
from iwa_rnaseq_reporter.app.deg_export_spec import (
    DegExportSummarySpec,
    DegExportRunMetadataSpec,
    DegExportPayload
)
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

def test_deg_export_summary_spec():
    spec = DegExportSummarySpec(
        comparison_column="group",
        group_a="A",
        group_b="B",
        comparison_label="A vs B",
        sample_count_group_a=3,
        sample_count_group_b=3
    )
    d = spec.to_dict()
    assert d["group_a"] == "A"
    assert d["sample_count_group_a"] == 3

def test_deg_export_payload_properties():
    summary = DegExportSummarySpec("col", "a", "b", "l", 1, 1)
    metadata = DegExportRunMetadataSpec("kind", True, True, 1, 0.0, 0.05, 1.0, "padj", 100)
    metrics = DegSummaryMetrics(100, 10, 5, 5.0)
    
    payload = DegExportPayload(
        summary=summary,
        metadata=metadata,
        result_table=pd.DataFrame({"G1": [1]}),
        summary_metrics=metrics
    )
    
    assert payload.has_results is True
    assert payload.summary.group_a == "a"
