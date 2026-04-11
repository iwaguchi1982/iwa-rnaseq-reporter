import pytest
import zipfile
import io
import json
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ComparatorConsensusContext,
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ComparatorConsensusSummarySpec,
    ConsensusSupportingReferenceSpec
)
from iwa_rnaseq_reporter.app.comparator_consensus_export_builder import (
    build_consensus_run_id,
    build_consensus_export_payload,
    build_consensus_export_bundle,
    build_consensus_report_summary_md
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff_builder import (
    build_consensus_handoff_payload,
    serialize_handoff_contract
)
from iwa_rnaseq_reporter.app.comparator_ranking import (
    ComparatorRankingContext,
    ComparatorRankingSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_ranking_input import (
    ComparatorRankingInputContext,
    ComparatorRankingInputSummarySpec
)

def _create_real_ranking_ctx():
    input_sum = ComparatorRankingInputSummarySpec(0, 0, 0, 0, False, True)
    input_ctx = ComparatorRankingInputContext(MagicMock(), (), (), (), input_sum)
    sum_out = ComparatorRankingSummarySpec(0, 0, 0, True)
    return ComparatorRankingContext(input_ctx, (), (), (), sum_out)

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
        ranking_context=_create_real_ranking_ctx(),
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
    assert payload.manifest.schema_name == "ConsensusExportManifest"
    assert payload.manifest.schema_version == "0.19.3"
    assert payload.manifest.generated_at is not None
    assert payload.manifest.provenance.producer_app == "iwa_rnaseq_reporter"
    assert payload.decision_rows[0].comparison_id == "c1"

def test_build_bundle_zip_contents():
    dec = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor", ())
    prof = ConsensusEvidenceProfileSpec("c1", None, (), (), (), 0.1, False, False)
    summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
    
    ctx = ComparatorConsensusContext(
        ranking_context=_create_real_ranking_ctx(),
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
        
        # Verify JSON content (light check)
        manifest_data = json.loads(zf.read("consensus_manifest.json"))
        assert manifest_data["schema_name"] == "ConsensusExportManifest"
        assert manifest_data["provenance"]["producer_app"] == "iwa_rnaseq_reporter"

def test_handoff_contract_integrity():
    dec = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor", ())
    prof = ConsensusEvidenceProfileSpec("c1", None, (), (), (), 0.1, False, False)
    summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
    
    ctx = ComparatorConsensusContext(
        ranking_context=_create_real_ranking_ctx(),
        decisions=(dec,),
        evidence_profiles=(prof,),
        issues=(),
        summary=summary
    )
    
    payload = build_consensus_export_payload(ctx, "test_run")
    handoff = build_consensus_handoff_payload(ctx, payload, "test_bundle.zip")
    
    assert handoff.consensus_run_id == "test_run"
    assert handoff.schema_name == "ConsensusHandoffContract"
    assert handoff.generated_at is not None
    assert handoff.provenance.source_consensus_run_id == "test_run"
    assert "TUMOR" in handoff.decided_label_keys

def test_summary_markdown_polished_content():
    # Setup multiple statuses
    dec1 = ConsensusDecisionSpec("c1", "consensus", "TUMOR", "Tumor", ("top_rank",))
    
    # Create 5 dummy supporting refs
    sup_refs = tuple(
        ConsensusSupportingReferenceSpec("c1", "TUMOR", "DS1", f"C{i}", 0.9, i)
        for i in range(5)
    )
    prof1 = ConsensusEvidenceProfileSpec(
        comparison_id="c1",
        top_candidate=None,
        competing_candidates=(),
        supporting_references=sup_refs,
        conflicting_references=(),
        support_margin=0.1234,
        has_conflict=False,
        has_weak_support=False
    )
    
    dec2 = ConsensusDecisionSpec("c2", "abstain", None, None, ("insufficient_info",))
    prof2 = ConsensusEvidenceProfileSpec("c2", None, (), (), (), None, False, True)
    

    summary = ComparatorConsensusSummarySpec(2, 1, 1, 0, 0, True)
    
    ctx = ComparatorConsensusContext(
        ranking_context=_create_real_ranking_ctx(),
        decisions=(dec1, dec2),
        evidence_profiles=(prof1, prof2),
        issues=(),
        summary=summary
    )
    
    payload = build_consensus_export_payload(ctx, "test_run")
    md = build_consensus_report_summary_md(payload)
    
    # 1. Execution Summary
    assert "Abstained / Withheld: 1" in md
    
    # 2. Table headers
    assert "| Support | Conflict | Weak Support | Reason |" in md
    
    # 3. Row content
    assert "0.123" in md  # 3-decimal margin for c1
    assert "| 5 | no | no | top_rank |" in md  # c1 evidence stats
    assert "| 0 | no | yes | insufficient_info |" in md  # c2 evidence stats (fallback for abstain)
    
    # 4. Sections
    assert "## Decision Support Snapshot" in md
    assert "## Decision Support Quick Lookup" in md
    assert "clear label selected" in md

def test_summary_markdown_mixed_status_snapshot():
    # 4 statuses
    decs = [
        ConsensusDecisionSpec("c1", "consensus", "L1", "D1", ()),
        ConsensusDecisionSpec("c2", "no_consensus", None, None, ("conflict",)),
        ConsensusDecisionSpec("c3", "insufficient_evidence", None, None, ()),
        ConsensusDecisionSpec("c4", "abstain", None, None, ())
    ]
    summary = ComparatorConsensusSummarySpec(4, 1, 1, 1, 1, True)
    ctx = ComparatorConsensusContext(
        ranking_context=_create_real_ranking_ctx(),
        decisions=tuple(decs),
        evidence_profiles=(),
        issues=(),
        summary=summary
    )
    payload = build_consensus_export_payload(ctx, "test_run")
    md = build_consensus_report_summary_md(payload)
    
    # Check Snapshot bucket formatting
    assert "- Consensus: 1 (c1)" in md
    assert "- No Consensus: 1 (c2)" in md
    assert "- Insufficient Evidence: 1 (c3)" in md
    assert "- Abstain: 1 (c4)" in md

def test_summary_markdown_fallback_behavior():
    # Payload with missing profiles
    dec = ConsensusDecisionSpec("c1", "consensus", "L1", "D1", ("code_a",))
    summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
    ctx = ComparatorConsensusContext(
        ranking_context=_create_real_ranking_ctx(),
        decisions=(dec,),
        evidence_profiles=(), # EMPTY
        issues=(),
        summary=summary
    )
    payload = build_consensus_export_payload(ctx, "test_run")
    md = build_consensus_report_summary_md(payload)
    
    # Check fallback values in table row for c1
    # margin=-, support=0, conflict=no, weak support=yes (as per spec 210-213)
    assert "| c1 | `consensus` | D1 | - | 0 | no | yes | code_a |" in md
