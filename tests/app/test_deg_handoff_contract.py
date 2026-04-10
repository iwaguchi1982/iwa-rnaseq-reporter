import pytest
import re
from iwa_rnaseq_reporter.app.deg_handoff_contract import (
    build_deg_comparison_id,
    DegHandoffIdentitySpec,
    DegHandoffDataRefSpec,
    DegHandoffPayload
)

def test_build_deg_comparison_id():
    """
    Verify deterministic ID generation.
    """
    comp_id = build_deg_comparison_id("Group/Col", "Case 1", "Ctrl 2", "gene_tpm")
    # Non-alpha should be underscores, collapse multiple
    assert comp_id == "Group_Col__Case_1__vs__Ctrl_2__gene_tpm"
    
    # Stable across calls
    assert build_deg_comparison_id("A", "B", "C", "D") == "A__B__vs__C__D"

def test_handoff_payload_to_dict():
    """
    Verify dict serialization for JSON export.
    """
    identity = DegHandoffIdentitySpec("id1", "label", "col", "a", "b")
    refs = DegHandoffDataRefSpec("bundle.zip")
    payload = DegHandoffPayload(
        identity=identity,
        analysis_metadata={"m": "v"},
        artifact_refs=refs,
        summary_metrics={"s": 1}
    )
    
    d = payload.to_dict()
    assert d["identity"]["comparison_id"] == "id1"
    assert d["artifact_refs"]["bundle_filename"] == "bundle.zip"
    assert d["artifact_refs"]["result_table_filename"] == "deg_results.csv"
