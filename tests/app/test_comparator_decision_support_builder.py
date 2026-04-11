import pytest
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ConsensusLabelCandidateSpec,
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

def test_top_reference_selection_and_sorting():
    from iwa_rnaseq_reporter.app.comparator_ranking import (
        ComparatorRankedReferenceSpec,
        ComparatorIntegratedRankingScoreSpec
    )
    from iwa_rnaseq_reporter.app.comparator_engine import ComparatorScoreSpec
    
    dummy_score = ComparatorScoreSpec(1, 1, 1, 1)
    dummy_norm = ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5)
    
    # helper to build complex mock
    def make_ref(ds_id, comp_id, rank, score):
        i_score = ComparatorIntegratedRankingScoreSpec(score, None, None, None, None)
        return ComparatorRankedReferenceSpec(
            "C1", ds_id, comp_id, rank, i_score, dummy_score, dummy_norm
        )
    
    r1 = make_ref("DS1", "C1", 2, 0.8)
    r2 = make_ref("DS2", "C2", 1, 0.9)
    r3 = make_ref("DS3", "C3", 3, 0.7)
    r4 = make_ref("DS4", "C4", 2, 0.9) # Identical score to r2 but rank 2
    
    # Sort order should be: r2 (0.9, R1), r4 (0.9, R2), r1 (0.8, R2), r3 (0.7, R3)
    top_refs = build_top_reference_refs([r1, r2, r3, r4], max_refs=3)
    
    assert len(top_refs) == 3
    assert top_refs[0].reference_dataset_id == "DS2"
    assert top_refs[1].reference_dataset_id == "DS4"
    assert top_refs[2].reference_dataset_id == "DS1"
    assert top_refs[0].integrated_score == 0.9

def test_decision_support_payload_orchestration():
    # Setup mock context
    decision = ConsensusDecisionSpec("COMP1", "consensus", "L1", "Lab1", ("reason",))
    
    top_cand = ConsensusLabelCandidateSpec("COMP1", "L1", "Lab1", 1, 0.8, 0.8)
    profile = ConsensusEvidenceProfileSpec(
        comparison_id="COMP1",
        top_candidate=top_cand,
        competing_candidates=(),
        supporting_references=(),
        conflicting_references=(),
        support_margin=0.2,
        has_conflict=False,
        has_weak_support=False
    )
    
    # Minimal context setup
    class MockContext:
        def __init__(self):
            self.decisions = [decision]
            self.evidence_profiles = [profile]
            self.summary = {"n_consensus": 1}
            # Add dummy ranking context to satisfy payload builder if needed
            self.ranking_context = type('obj', (object,), {'ranking_config': None})
            self.consensus_config = None

    ctx = MockContext()
    bundle_refs = ComparatorConsensusBundleRefSpec("f", "m", "s", "d", "e", "h")
    
    payload = build_decision_support_payload(ctx, bundle_refs)
    
    assert len(payload.decision_evidence_refs) == 1
    ref = payload.decision_evidence_refs[0]
    assert ref.comparison_id == "COMP1"
    assert ref.decision_status == "consensus"
    assert ref.evidence_stats.support_margin == 0.2
    assert payload.summary.n_consensus == 1
    assert payload.summary.n_decision_refs == 1
