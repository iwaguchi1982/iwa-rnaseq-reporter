import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.reference_dataset_registry import (
    ReferenceDatasetRegistry,
    ReferenceDatasetSpec,
    ReferenceComparisonSpec
)
from iwa_rnaseq_reporter.app.comparator_ranking import (
    ComparatorRankingContext,
    ComparatorRankedReferenceSpec,
    ComparatorIntegratedRankingScoreSpec,
    ComparatorRankingSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_consensus_builder import (
    resolve_consensus_label_for_reference,
    build_consensus_label_candidates,
    build_consensus_decision,
    build_comparator_consensus_context
)

def test_resolve_consensus_label_fallback():
    # Setup registry with missing labels
    rc = ReferenceComparisonSpec("rc1", "Raw Label", "A", "B", "ref1")
    ds = ReferenceDatasetSpec("ds1", "Dataset", "src", "human", "count", "ens", (rc,))
    registry = ReferenceDatasetRegistry((ds,))
    
    lk, ld = resolve_consensus_label_for_reference("ds1", "rc1", registry)
    assert lk == "rc1"      # Fallback to ID
    assert ld == "Raw Label" # Fallback to comparison_label

def test_resolve_consensus_label_with_enriched_fields():
    # Setup registry with explicit labels
    rc = ReferenceComparisonSpec(
        "rc1", "Raw Label", "A", "B", "ref1",
        consensus_label_key="TUMOR",
        consensus_label_display="Tumor-like State"
    )
    ds = ReferenceDatasetSpec("ds1", "Dataset", "src", "human", "count", "ens", (rc,))
    registry = ReferenceDatasetRegistry((ds,))
    
    lk, ld = resolve_consensus_label_for_reference("ds1", "rc1", registry)
    assert lk == "TUMOR"
    assert ld == "Tumor-like State"

def _create_mock_ranked_ref(cid, dsid, score, rank):
    m = MagicMock(spec=ComparatorRankedReferenceSpec)
    m.comparison_id = cid
    m.reference_dataset_id = dsid
    m.reference_comparison_id = "rc1"
    m.rank = rank
    m.integrated_score = MagicMock(spec=ComparatorIntegratedRankingScoreSpec)
    m.integrated_score.integrated_score = score
    return m

def test_consensus_decision_logic():
    # 1. Clear Consensus (Margin 0.1)
    # top_candidate.mean = 0.8, competing[0].mean = 0.7 -> Margin 0.1
    profile_ok = MagicMock()
    profile_ok.comparison_id = "c1"
    profile_ok.top_candidate.label_key = "TUMOR"
    profile_ok.top_candidate.label_display = "Tumor"
    profile_ok.top_candidate.n_supporting_references = 2
    profile_ok.support_margin = 0.1
    
    dec = build_consensus_decision(profile_ok, has_top_rank_conflict=False)
    assert dec.decision_status == "consensus"
    assert dec.decided_label_key == "TUMOR"

    # 2. No Consensus (Low Margin)
    profile_bad = MagicMock()
    profile_bad.comparison_id = "c2"
    profile_bad.top_candidate.label_key = "TUMOR"
    profile_bad.top_candidate.n_supporting_references = 2
    profile_bad.support_margin = 0.02 # < 0.05
    
    dec = build_consensus_decision(profile_bad, has_top_rank_conflict=False)
    assert dec.decision_status == "no_consensus"
    assert "weak_support_margin" in dec.reason_codes

def test_build_consensus_context_full_flow():
    # Ranking Context Mock
    # 2 refs pointing to same TUMOR label
    r1 = _create_mock_ranked_ref("comp_A", "ds1", 0.9, 1)
    
    # Registry matches labels
    rc = ReferenceComparisonSpec("rc1", "Tumor vs Normal", "T", "N", "ref1", "TUMOR", "Tumor")
    ds = ReferenceDatasetSpec("ds1", "DS", "src", "H", "C", "E", (rc,))
    registry = ReferenceDatasetRegistry((ds,))
    
    summary = MagicMock(spec=ComparatorRankingSummarySpec)
    summary.is_ready_for_reference_ranking = True
    
    rank_ctx = MagicMock(spec=ComparatorRankingContext)
    rank_ctx.ranked_references = (r1,)
    rank_ctx.top_rank_conflicts = ()
    rank_ctx.summary = summary
    
    consensus_ctx = build_comparator_consensus_context(rank_ctx, registry)
    
    assert consensus_ctx.summary.n_consensus == 1
    assert consensus_ctx.decisions[0].decided_label_key == "TUMOR"
    assert len(consensus_ctx.evidence_profiles[0].supporting_references) == 1
