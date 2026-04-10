import pytest
import zipfile
import io
import json
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ComparatorConsensusContext,
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ComparatorConsensusSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_consensus_export_builder import (
    build_consensus_run_id,
    build_consensus_export_payload,
    build_consensus_export_bundle
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff_builder import (
    build_consensus_handoff_payload,
    serialize_handoff_contract
)

def test_build_export_payload_basics():
    # Use real dataclasses to avoid MagicMock serialization issues
    dec = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor Label", ())
    prof = ConsensusEvidenceProfileSpec(
        comparison_id="c1",
        top_candidate=None,
        competing_candidates=(),
        supporting_references=(),
        conflicting_references=(),
        support_margin=0.1,
        has_conflict=False,
        has_weak_support=False
    )
    
    summary = ComparatorConsensusSummarySpec(1, 1, 5, 0, 0, True)
    
    # rank_ctx is needed for ComparatorConsensusContext, use a dummy or mock
    # because it won't be serialized in the payload's direct JSON calls in the test
    # (The payload only contains pieces of it)
    ctx = ComparatorConsensusContext(
        ranking_context=MagicMock(),
        decisions=(dec,),
        evidence_profiles=(prof,),
        issues=(),
        summary=summary
    )
    
    run_id = build_consensus_run_id()
    payload = build_consensus_export_payload(ctx, run_id)
    
    assert payload.manifest.consensus_run_id == run_id
    assert payload.manifest.n_consensus == 1
    assert payload.manifest.n_abstain == 5
    assert payload.decision_rows[0].comparison_id == "c1"

def test_build_bundle_zip_contents():
    dec = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor", ())
    prof = ConsensusEvidenceProfileSpec("c1", None, (), (), (), 0.1, False, False)
    summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
    
    ctx = ComparatorConsensusContext(
        ranking_context=MagicMock(),
        decisions=(dec,),
        evidence_profiles=(prof,),
        issues=(),
        summary=summary
    )
    
    payload = build_consensus_export_payload(ctx, "test_run")
    handoff_json = "{}"
    
    bundle_bytes = build_consensus_export_bundle(payload, handoff_json)
    
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        file_list = zf.namelist()
        assert "consensus_manifest.json" in file_list
        assert "consensus_decisions.json" in file_list
        assert "consensus_decisions.csv" in file_list

def test_handoff_contract_integrity():
    dec = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor", ())
    prof = ConsensusEvidenceProfileSpec("c1", None, (), (), (), 0.1, False, False)
    summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
    
    ctx = ComparatorConsensusContext(
        ranking_context=MagicMock(),
        decisions=(dec,),
        evidence_profiles=(prof,),
        issues=(),
        summary=summary
    )
    
    payload = build_consensus_export_payload(ctx, "test_run")
    handoff = build_consensus_handoff_payload(ctx, payload, "test_bundle.zip")
    
    assert handoff.consensus_run_id == "test_run"
    assert "TUMOR" in handoff.decided_label_keys
