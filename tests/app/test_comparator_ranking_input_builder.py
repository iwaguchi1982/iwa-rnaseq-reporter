import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_engine import (
    ComparatorScoreSpec,
    ComparatorResultContext,
    ComparatorMatchResultSpec,
    ComparatorResultSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_score_normalizer import (
    normalize_overlap_score,
    normalize_correlation_score,
    build_normalized_score
)
from iwa_rnaseq_reporter.app.comparator_ranking_input_builder import (
    is_match_rankable,
    build_comparator_ranking_input_context
)

def test_normalization_logic():
    # 1. Overlap Scaling (Cap = 500)
    assert normalize_overlap_score(0) == 0.0
    assert normalize_overlap_score(250) == 0.5
    assert normalize_overlap_score(500) == 1.0
    assert normalize_overlap_score(1000) == 1.0 # Capped

    # 2. Correlation Mapping ([-1, 1] -> [0, 1])
    assert normalize_correlation_score(None) is None
    assert normalize_correlation_score(-1.0) == 0.0
    assert normalize_correlation_score(0.0) == 0.5
    assert normalize_correlation_score(1.0) == 1.0

def test_build_normalized_score():
    raw = ComparatorScoreSpec(250, 50, 0.8, 0.0)
    norm = build_normalized_score(raw, top_n=100, overlap_cap=500)
    
    assert norm.overlap_score == 0.5
    assert norm.top_n_overlap_score == 0.5
    assert norm.concordance_score == 0.8
    assert norm.correlation_score == 0.5

def test_eligibility_logic():
    # Rankable
    raw_ok = ComparatorScoreSpec(10, 5, 0.8, 0.5)
    is_ok, reasons = is_match_rankable(raw_ok)
    assert is_ok is True
    assert not reasons

    # Not Rankable: Zero overlap
    raw_bad1 = ComparatorScoreSpec(0, 0, 0.8, 0.5)
    is_ok, reasons = is_match_rankable(raw_bad1)
    assert is_ok is False
    assert "zero_overlap" in reasons

    # Not Rankable: Missing values
    raw_bad2 = ComparatorScoreSpec(10, 5, None, None)
    is_ok, reasons = is_match_rankable(raw_bad2)
    assert is_ok is False
    assert "missing_concordance" in reasons
    assert "missing_correlation" in reasons

def test_build_ranking_input_context_flow():
    # Mock Result Context
    mock_res = MagicMock(spec=ComparatorMatchResultSpec)
    mock_res.comparison_id = "c1"
    mock_res.reference_dataset_id = "ds1"
    mock_res.reference_comparison_id = "rc1"
    mock_res.score = ComparatorScoreSpec(100, 20, 0.7, 0.3)
    
    summary = ComparatorResultSummarySpec(1, 1, 0, 1, True)
    
    result_ctx = ComparatorResultContext(
        matching_context=MagicMock(),
        match_results=(mock_res,),
        skipped_matches=(),
        issues=(),
        summary=summary
    )
    
    # Run Builder
    rank_ctx = build_comparator_ranking_input_context(result_ctx)
    
    assert rank_ctx.summary.n_rankable_matches == 1
    assert rank_ctx.summary.is_ready_for_reference_ranking is True
    assert rank_ctx.rankable_matches[0].comparison_id == "c1"
    assert rank_ctx.rankable_matches[0].normalized_score.overlap_score == 0.2 # 100/500

def test_ranking_input_not_ready_if_no_rankable():
    # Successful match but non-rankable (zero top-n overlap)
    mock_res = MagicMock(spec=ComparatorMatchResultSpec)
    mock_res.comparison_id = "c1"
    mock_res.reference_dataset_id = "ds1"
    mock_res.reference_comparison_id = "rc1"
    mock_res.score = ComparatorScoreSpec(100, 0, 0.7, 0.3) # zero_top_n_overlap
    
    summary = ComparatorResultSummarySpec(1, 1, 0, 1, True)
    result_ctx = ComparatorResultContext(
        matching_context=MagicMock(),
        match_results=(mock_res,),
        skipped_matches=(),
        issues=(),
        summary=summary
    )
    
    rank_ctx = build_comparator_ranking_input_context(result_ctx)
    
    assert rank_ctx.summary.n_rankable_matches == 0
    assert rank_ctx.summary.n_non_rankable_matches == 1
    assert rank_ctx.summary.is_ready_for_reference_ranking is False
    assert len(rank_ctx.issues) == 1
    assert rank_ctx.issues[0].issue_code == "all_matches_non_rankable"
