import pytest
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ConsensusLabelCandidateSpec,
    ConsensusSupportingReferenceSpec,
    ConsensusConflictingReferenceSpec,
    ComparatorConsensusContext,
    ComparatorRankingContext
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff import (
    ComparatorConsensusBundleRefSpec,
    ComparatorConsensusHandoffPayload
)
from iwa_rnaseq_reporter.app.comparator_decision_support_builder import (
    build_decision_support_payload,
    build_top_reference_refs,
    build_decision_evidence_stats
)
from iwa_rnaseq_reporter.app.comparator_ranking_input import ComparatorNormalizedScoreSpec

def test_build_decision_evidence_stats_fallback():
    # Profile is None
    stats = build_decision_evidence_stats(None)
    assert stats.has_weak_support is True
    assert stats.n_supporting_references == 0
    assert stats.support_margin is None

def test_top_reference_selection_and_sorting_with_real_specs():
    """
    Ensure sorting works with real float-based specs.
    Corresponds to spec 6-1.
    """
    # Create real SupportingRef instances (score is float)
    # Order: comp_id, label_key, ds_id, ref_comp_id, score, rank
    r1 = ConsensusSupportingReferenceSpec("C1", "L1", "DS1", "D1_C1", 0.8, 2)
    r2 = ConsensusSupportingReferenceSpec("C1", "L1", "DS2", "D2_C1", 0.9, 1)
    r3 = ConsensusSupportingReferenceSpec("C1", "L1", "DS3", "D3_C1", 0.7, 3)
    r4 = ConsensusSupportingReferenceSpec("C1", "L1", "DS4", "D4_C1", 0.9, 2)
    
    # Sort order: r2 (0.9, R1), r4 (0.9, R2), r1 (0.8, R2), r3 (0.7, R3)
    top_refs = build_top_reference_refs([r1, r2, r3, r4], max_refs=3)
    
    assert len(top_refs) == 3
    assert top_refs[0].reference_dataset_id == "DS2"
    assert top_refs[1].reference_dataset_id == "DS4"
    assert top_refs[2].reference_dataset_id == "DS1"
    assert top_refs[0].integrated_score == 0.9

def test_decision_support_payload_orchestration_with_evidence():
    """
    Verify orchestration with non-empty evidence refs.
    Corresponds to spec 6-2.
    """
    # Setup mock context
    decision = ConsensusDecisionSpec("COMP1", "consensus", "L1", "Lab1", ("reason",))
    
    # Supporting refs
    s1 = ConsensusSupportingReferenceSpec("COMP1", "L1", "DS1", "D1_C1", 0.8, 1)
    s2 = ConsensusSupportingReferenceSpec("COMP1", "L1", "DS2", "D2_C1", 0.7, 2)
    # Conflicting ref
    c1 = ConsensusConflictingReferenceSpec("COMP1", "L2", "DS3", "D3_C1", 0.6, 1)
    
    top_cand = ConsensusLabelCandidateSpec("COMP1", "L1", "Lab1", 1, 0.8, 0.8)
    profile = ConsensusEvidenceProfileSpec(
        comparison_id="COMP1",
        top_candidate=top_cand,
        competing_candidates=(),
        supporting_references=(s1, s2),
        conflicting_references=(c1,),
        support_margin=0.2,
        has_conflict=True,
        has_weak_support=False
    )
    
    # Minimal context setup
    class MockContext:
        def __init__(self):
            self.decisions = [decision]
            self.evidence_profiles = [profile]
            self.summary = {"n_consensus": 1}
            self.ranking_context = type('obj', (object,), {'ranking_config': None})
            self.consensus_config = None

    ctx = MockContext()
    bundle_refs = ComparatorConsensusBundleRefSpec("f", "m", "s", "d", "e", "h")
    
    payload = build_decision_support_payload(ctx, bundle_refs)
    
    assert len(payload.decision_evidence_refs) == 1
    ref = payload.decision_evidence_refs[0]
    assert ref.comparison_id == "COMP1"
    
    # stats
    assert ref.evidence_stats.n_supporting_references == 2
    assert ref.evidence_stats.n_conflicting_references == 1
    assert ref.evidence_stats.has_conflict is True
    
    # top refs
    assert len(ref.top_supporting_reference_refs) == 2
    assert ref.top_supporting_reference_refs[0].reference_dataset_id == "DS1"
    assert len(ref.top_conflicting_reference_refs) == 1
    assert ref.top_conflicting_reference_refs[0].reference_dataset_id == "DS3"

    assert payload.summary.n_consensus == 1
