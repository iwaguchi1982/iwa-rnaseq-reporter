from typing import Dict, List, Optional, Tuple
from .comparator_ranking_input import (
    ComparatorNormalizedScoreSpec,
    ComparatorRankableMatchSpec,
    ComparatorRankingInputContext
)
from .comparator_ranking import (
    ComparatorIntegratedRankingScoreSpec,
    ComparatorRankedReferenceSpec,
    ComparatorTopRankConflictSpec,
    ComparatorRankingIssueSpec,
    ComparatorRankingSummarySpec,
    ComparatorRankingContext
)

def compute_integrated_ranking_score(
    normalized_score: ComparatorNormalizedScoreSpec,
    overlap_weight: float = 0.20,
    top_n_overlap_weight: float = 0.30,
    concordance_weight: float = 0.20,
    correlation_weight: float = 0.30
) -> ComparatorIntegratedRankingScoreSpec:
    """
    Calculate a single weighted score from normalized components according to spec 6-1.
    """
    # Defensive handling of None values (though rankable matches should have these keys)
    o = normalized_score.overlap_score or 0.0
    tn = normalized_score.top_n_overlap_score or 0.0
    cn = normalized_score.concordance_score or 0.0
    cr = normalized_score.correlation_score or 0.0
    
    integrated = (
        (o * overlap_weight) +
        (tn * top_n_overlap_weight) +
        (cn * concordance_weight) +
        (cr * correlation_weight)
    )
    
    return ComparatorIntegratedRankingScoreSpec(
        integrated_score=integrated,
        overlap_component=o * overlap_weight,
        top_n_overlap_component=tn * top_n_overlap_weight,
        concordance_component=cn * concordance_weight,
        correlation_component=cr * correlation_weight
    )

def rank_references_for_comparison(
    comparison_id: str,
    matches: Tuple[ComparatorRankableMatchSpec, ...],
    tie_tolerance: float = 0.02
) -> Tuple[Tuple[ComparatorRankedReferenceSpec, ...], Optional[ComparatorTopRankConflictSpec]]:
    """
    Rank references for a single experimental comparison and detect top-rank conflicts.
    """
    if not matches:
        return (), None
    
    # 1. Compute Integrated Scores
    scored_items = []
    for m in matches:
        int_score = compute_integrated_ranking_score(m.normalized_score)
        scored_items.append({
            "match": m,
            "int_score": int_score
        })
        
    # 2. Sort by Integrated Score (Primary) and Correlation (Secondary)
    # Spec 7-2
    scored_items.sort(
        key=lambda x: (
            x["int_score"].integrated_score,
            x["match"].normalized_score.correlation_score or 0.0,
            x["match"].reference_dataset_id
        ),
        reverse=True
    )
    
    # 3. Assign Ranks and Detect Conflicts
    ranked_refs = []
    top_score = scored_items[0]["int_score"].integrated_score
    top_ref_ids = []
    conflict_codes = []
    
    for i, item in enumerate(scored_items):
        match = item["match"]
        score_spec = item["int_score"]
        curr_score = score_spec.integrated_score
        
        # Determine flags for rank 1
        flags = []
        is_at_top = False
        if i == 0:
            flags.append("top_rank")
            is_at_top = True
        elif abs(curr_score - top_score) < 1e-9: # Exact tie
            flags.append("tie_with_top")
            is_at_top = True
        elif abs(curr_score - top_score) <= tie_tolerance:
            flags.append("near_tie_with_top")
            is_at_top = True
            
        if is_at_top:
            ref_id = f"{match.reference_dataset_id}:{match.reference_comparison_id}"
            top_ref_ids.append(ref_id)
            if i > 0:
                code = "exact_tie_at_top" if "tie_with_top" in flags else "near_tie_at_top"
                if code not in conflict_codes:
                    conflict_codes.append(code)

        ranked_refs.append(ComparatorRankedReferenceSpec(
            comparison_id=comparison_id,
            reference_dataset_id=match.reference_dataset_id,
            reference_comparison_id=match.reference_comparison_id,
            rank=i + 1,
            integrated_score=score_spec,
            raw_score=match.raw_score,
            normalized_score=match.normalized_score,
            ranking_flags=tuple(flags)
        ))
        
    # 4. Finalize Conflict Spec
    conflict = None
    if len(top_ref_ids) > 1:
        conflict = ComparatorTopRankConflictSpec(
            comparison_id=comparison_id,
            top_reference_ids=tuple(top_ref_ids),
            reason_codes=tuple(conflict_codes)
        )
        
    return tuple(ranked_refs), conflict

def build_comparator_ranking_context(
    ranking_input_context: ComparatorRankingInputContext,
    tie_tolerance: float = 0.02
) -> ComparatorRankingContext:
    """
    Orchestrate the ranking phase for the entire portfolio.
    """
    # 1. Group by comparison_id
    grouped_matches: Dict[str, List[ComparatorRankableMatchSpec]] = {}
    for m in ranking_input_context.rankable_matches:
        if m.comparison_id not in grouped_matches:
            grouped_matches[m.comparison_id] = []
        grouped_matches[m.comparison_id].append(m)
        
    # 2. Perform Ranking
    all_ranked_refs: List[ComparatorRankedReferenceSpec] = []
    all_conflicts: List[ComparatorTopRankConflictSpec] = []
    issues: List[ComparatorRankingIssueSpec] = []
    ranked_comparison_ids = []
    
    for cid, matches in grouped_matches.items():
        ranked, conflict = rank_references_for_comparison(cid, tuple(matches), tie_tolerance)
        all_ranked_refs.extend(ranked)
        if conflict:
            all_conflicts.append(conflict)
        ranked_comparison_ids.append(cid)
        
    # 3. Summary & Readiness
    is_ready = (
        ranking_input_context.summary.is_ready_for_reference_ranking and
        len(ranked_comparison_ids) > 0
    )
    
    summary = ComparatorRankingSummarySpec(
        n_rankable_matches=len(ranking_input_context.rankable_matches),
        n_ranked_comparisons=len(ranked_comparison_ids),
        n_top_rank_conflicts=len(all_conflicts),
        is_ready_for_consensus_labeling=is_ready
    )
    
    return ComparatorRankingContext(
        ranking_input_context=ranking_input_context,
        ranked_references=tuple(all_ranked_refs),
        top_rank_conflicts=tuple(all_conflicts),
        issues=tuple(issues),
        summary=summary
    )
