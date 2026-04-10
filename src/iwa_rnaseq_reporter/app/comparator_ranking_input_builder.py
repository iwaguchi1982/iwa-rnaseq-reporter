from typing import List, Set, Tuple
from .comparator_engine import ComparatorResultContext, ComparatorScoreSpec
from .comparator_ranking_input import (
    ComparatorNormalizedScoreSpec,
    ComparatorRankableMatchSpec,
    ComparatorNonRankableMatchSpec,
    ComparatorRankingIssueSpec,
    ComparatorRankingInputSummarySpec,
    ComparatorRankingInputContext
)
from .comparator_score_normalizer import build_normalized_score

def is_match_rankable(
    raw_score: ComparatorScoreSpec
) -> Tuple[bool, Tuple[str, ...]]:
    """
    Determine if a match has sufficient statistical strength to be ranked.
    Returns (is_rankable, reason_codes).
    """
    reasons = []
    
    if raw_score.n_overlap_features <= 0:
        reasons.append("zero_overlap")
    
    if raw_score.n_top_n_overlap_features <= 0:
        reasons.append("zero_top_n_overlap")
        
    if raw_score.direction_concordance is None:
        reasons.append("missing_concordance")
        
    if raw_score.signed_effect_correlation is None:
        reasons.append("missing_correlation")
        
    if reasons:
        # Add a general code if any specific lack of evidence was found
        reasons.append("insufficient_evidence_for_ranking")
        return False, tuple(reasons)
        
    return True, ()

def build_comparator_ranking_input_context(
    result_context: ComparatorResultContext,
    top_n: int = 100,
    overlap_cap: int = 500
) -> ComparatorRankingInputContext:
    """
    Orchestrate the transformation from raw match results to normalized ranking inputs.
    """
    rankable_matches: List[ComparatorRankableMatchSpec] = []
    non_rankable_matches: List[ComparatorNonRankableMatchSpec] = []
    issues: List[ComparatorRankingIssueSpec] = []
    
    # Process successful matches from the engine
    for res in result_context.match_results:
        cid = res.comparison_id
        ds_id = res.reference_dataset_id
        rc_id = res.reference_comparison_id
        raw_score = res.score
        
        is_rankable, reasons = is_match_rankable(raw_score)
        
        if is_rankable:
            normalized = build_normalized_score(raw_score, top_n, overlap_cap)
            rankable_matches.append(ComparatorRankableMatchSpec(
                comparison_id=cid,
                reference_dataset_id=ds_id,
                reference_comparison_id=rc_id,
                raw_score=raw_score,
                normalized_score=normalized
            ))
        else:
            non_rankable_matches.append(ComparatorNonRankableMatchSpec(
                comparison_id=cid,
                reference_dataset_id=ds_id,
                reference_comparison_id=rc_id,
                reason_codes=reasons
            ))

    # Aggregate Issues
    if not rankable_matches and result_context.match_results:
        issues.append(ComparatorRankingIssueSpec(
            issue_code="all_matches_non_rankable",
            severity="warning",
            message="Matches exist but none passed eligibility criteria for ranking."
        ))
    
    # Summary
    rankable_comparison_set: Set[str] = {m.comparison_id for m in rankable_matches}
    
    is_ready = (
        result_context.summary.is_ready_for_export and
        len(rankable_matches) > 0
    )
    
    summary = ComparatorRankingInputSummarySpec(
        n_successful_matches=len(result_context.match_results),
        n_rankable_matches=len(rankable_matches),
        n_non_rankable_matches=len(non_rankable_matches),
        n_comparisons_with_rankable_matches=len(rankable_comparison_set),
        has_only_weak_evidence=(len(rankable_matches) == 0 and len(non_rankable_matches) > 0),
        is_ready_for_reference_ranking=is_ready
    )

    return ComparatorRankingInputContext(
        result_context=result_context,
        rankable_matches=tuple(rankable_matches),
        non_rankable_matches=tuple(non_rankable_matches),
        issues=tuple(issues),
        summary=summary
    )
