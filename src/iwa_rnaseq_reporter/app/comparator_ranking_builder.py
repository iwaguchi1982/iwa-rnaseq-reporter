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
from .comparator_execution_config import RankingConfigSpec, build_default_ranking_config

def compute_integrated_ranking_score(
    normalized_score: ComparatorNormalizedScoreSpec,
    config: Optional[RankingConfigSpec] = None
) -> ComparatorIntegratedRankingScoreSpec:
    """
    Calculate a single weighted score from normalized components according to execution config.
    """
    cfg = config if config else build_default_ranking_config()
    
    # Defensive handling of None values
    o = normalized_score.overlap_score or 0.0
    tn = normalized_score.top_n_overlap_score or 0.0
    cn = normalized_score.concordance_score or 0.0
    cr = normalized_score.correlation_score or 0.0
    
    integrated = (
        (o * cfg.overlap_weight) +
        (tn * cfg.top_n_overlap_weight) +
        (cn * cfg.concordance_weight) +
        (cr * cfg.correlation_weight)
    )
    
    return ComparatorIntegratedRankingScoreSpec(
        integrated_score=integrated,
        overlap_component=o * cfg.overlap_weight,
        top_n_overlap_component=tn * cfg.top_n_overlap_weight,
        concordance_component=cn * cfg.concordance_weight,
        correlation_component=cr * cfg.correlation_weight
    )

def rank_references_for_comparison(
    comparison_id: str,
    matches: Tuple[ComparatorRankableMatchSpec, ...],
    ranking_config: Optional[RankingConfigSpec] = None
) -> Tuple[Tuple[ComparatorRankedReferenceSpec, ...], Optional[ComparatorTopRankConflictSpec]]:
    """
    Rank references for a single experimental comparison and detect top-rank conflicts using config.
    """
    if not matches:
        return (), None
    
    cfg = ranking_config if ranking_config else build_default_ranking_config()
    
    # 1. Compute Integrated Scores
    scored_items = []
    for m in matches:
        int_score = compute_integrated_ranking_score(m.normalized_score, config=cfg)
        scored_items.append({
            "match": m,
            "int_score": int_score
        })
        
    # 2. Sort by Integrated Score (Primary) and Correlation (Secondary)
    # Refined logic from v0.18.x with config awareness
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
        elif abs(curr_score - top_score) < cfg.exact_tie_epsilon: # Configurable exact tie
            flags.append("tie_with_top")
            is_at_top = True
        elif abs(curr_score - top_score) <= cfg.tie_tolerance: # Configurable near tie
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
    ranking_config: Optional[RankingConfigSpec] = None
) -> ComparatorRankingContext:
    """
    Orchestrate the ranking phase for the entire portfolio using the provided config.
    """
    cfg = ranking_config if ranking_config else build_default_ranking_config()
    
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
        ranked, conflict = rank_references_for_comparison(cid, tuple(matches), ranking_config=cfg)
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
        summary=summary,
        ranking_config=cfg
    )
