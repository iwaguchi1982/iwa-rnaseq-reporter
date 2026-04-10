import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_engine import ComparatorScoreSpec
from iwa_rnaseq_reporter.app.comparator_ranking_input import (
    ComparatorNormalizedScoreSpec,
    ComparatorRankableMatchSpec,
    ComparatorRankingInputContext,
    ComparatorRankingInputSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_ranking_builder import (
    compute_integrated_ranking_score,
    rank_references_for_comparison,
    build_comparator_ranking_context
)

def _create_mock_match(cid, dsid, normalized_score):
    m = MagicMock(spec=ComparatorRankableMatchSpec)
    m.comparison_id = cid
    m.reference_dataset_id = dsid
    m.reference_comparison_id = "rc1"
    m.normalized_score = normalized_score
    m.raw_score = MagicMock(spec=ComparatorScoreSpec)
    return m

def test_compute_integrated_ranking_score_basics():
    # All components 1.0 -> Score 1.0
    norm = ComparatorNormalizedScoreSpec(1.0, 1.0, 1.0, 1.0)
    res = compute_integrated_ranking_score(norm)
    assert res.integrated_score == pytest.approx(1.0)
    assert res.overlap_component == 0.2
    assert res.top_n_overlap_component == 0.3
    
    # Half values
    norm2 = ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5)
    res2 = compute_integrated_ranking_score(norm2)
    assert res2.integrated_score == pytest.approx(0.5)

def test_ranking_logic_order():
    m1 = _create_mock_match("c1", "ds1", ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5))
    m2 = _create_mock_match("c1", "ds2", ComparatorNormalizedScoreSpec(0.8, 0.8, 0.8, 0.8))
    
    ranked, conflict = rank_references_for_comparison("c1", (m1, m2))
    
    assert len(ranked) == 2
    assert ranked[0].reference_dataset_id == "ds2"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert conflict is None

def test_tie_conflict_detection():
    m1 = _create_mock_match("c1", "ds1", ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5))
    m2 = _create_mock_match("c1", "ds2", ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5))
    
    ranked, conflict = rank_references_for_comparison("c1", (m1, m2))
    
    assert conflict is not None
    assert "exact_tie_at_top" in conflict.reason_codes
    assert any("ds1" in tid for tid in conflict.top_reference_ids)
    assert any("ds2" in tid for tid in conflict.top_reference_ids)

def test_near_tie_conflict_detection():
    m1 = _create_mock_match("c1", "ds1", ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.5))
    # diff < 0.02
    m2 = _create_mock_match("c1", "ds2", ComparatorNormalizedScoreSpec(0.5, 0.5, 0.5, 0.46))
    
    ranked, conflict = rank_references_for_comparison("c1", (m1, m2), tie_tolerance=0.02)
    
    assert conflict is not None
    assert "near_tie_at_top" in conflict.reason_codes
    assert "near_tie_with_top" in ranked[1].ranking_flags

def test_build_ranking_context_full_flow():
    m1 = _create_mock_match("comp_A", "REF1", ComparatorNormalizedScoreSpec(0.6, 0.6, 0.6, 0.6))
    
    summary = MagicMock(spec=ComparatorRankingInputSummarySpec)
    summary.is_ready_for_reference_ranking = True
    
    input_ctx = MagicMock(spec=ComparatorRankingInputContext)
    input_ctx.rankable_matches = (m1,)
    input_ctx.summary = summary
    
    rank_ctx = build_comparator_ranking_context(input_ctx)
    
    assert rank_ctx.summary.n_ranked_comparisons == 1
    assert rank_ctx.summary.is_ready_for_consensus_labeling is True
    assert rank_ctx.ranked_references[0].comparison_id == "comp_A"
