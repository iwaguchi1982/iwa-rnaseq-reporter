import pytest
import dataclasses
from iwa_rnaseq_reporter.app.comparator_decision_support import (
    DecisionArtifactRefSpec,
    DecisionEvidenceStatsSpec,
    DecisionTopReferenceRefSpec,
    DecisionEvidenceRefSpec,
    ComparatorDecisionSupportSummarySpec,
    ComparatorDecisionSupportPayload
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff import (
    ComparatorConsensusHandoffPayload,
    ComparatorConsensusBundleRefSpec
)

def test_decision_support_spec_serialization():
    # 1. Artifact Refs
    art_refs = DecisionArtifactRefSpec(
        consensus_manifest_path="m.json",
        consensus_handoff_contract_path="h.json",
        consensus_decisions_json_path="d.json",
        evidence_profiles_json_path="e.json",
        consensus_decisions_csv_path="d.csv",
        report_summary_md_path="s.md"
    )
    
    # 2. Stats
    stats = DecisionEvidenceStatsSpec(
        support_margin=0.15,
        has_conflict=True,
        has_weak_support=False,
        n_supporting_references=3,
        n_conflicting_references=1,
        n_competing_candidates=2
    )
    
    # 3. Top Ref
    top_ref = DecisionTopReferenceRefSpec(
        reference_dataset_id="DS1",
        reference_comparison_id="COMP1",
        label_key="TUMOR",
        label_display="Tumor",
        integrated_score=0.85,
        rank=1
    )
    
    # 4. Evidence Ref
    ev_ref = DecisionEvidenceRefSpec(
        comparison_id="C1",
        decision_status="consensus",
        decided_label_key="TUMOR",
        decided_label_display="Tumor",
        reason_codes=("strong_consensus",),
        evidence_stats=stats,
        artifact_refs=art_refs,
        top_supporting_reference_refs=(top_ref,),
        top_conflicting_reference_refs=()
    )
    
    # 5. Summary
    summary = ComparatorDecisionSupportSummarySpec(1, 1, 0, 0, 0)
    
    # 6. Payload
    payload = ComparatorDecisionSupportPayload(
        decision_evidence_refs=(ev_ref,),
        summary=summary
    )
    
    assert payload.schema_version == "0.19.4.1"
    
    # Check serialization
    as_dict = dataclasses.asdict(payload)
    assert as_dict["schema_name"] == "ComparatorDecisionSupportPayload"
    assert as_dict["summary"]["n_consensus"] == 1
    assert as_dict["decision_evidence_refs"][0]["comparison_id"] == "C1"
    assert as_dict["decision_evidence_refs"][0]["evidence_stats"]["support_margin"] == 0.15

def test_handoff_payload_backward_compatibility():
    """
    Ensure the handoff payload can still be instantiated WITHOUT the new field.
    """
    bundle_refs = ComparatorConsensusBundleRefSpec("f", "m", "s", "d", "e", "h")
    
    # Instantiate without decision_support
    handoff = ComparatorConsensusHandoffPayload(
        consensus_run_id="run1",
        bundle_refs=bundle_refs,
        included_comparison_ids=("c1",),
        decided_label_keys=("L1",),
        comparison_decision_refs=(),
        summary={},  # Use empty dict for summary as it's typically ComparatorConsensusSummarySpec
        generated_at="2026-04-11T00:00:00Z"
    )
    
    assert handoff.decision_support is None
    
    # Check that it still has schema info
    assert handoff.schema_version == "0.19.3"
