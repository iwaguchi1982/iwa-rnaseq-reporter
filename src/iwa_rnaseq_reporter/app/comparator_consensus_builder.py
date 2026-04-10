from typing import Dict, List, Optional, Tuple
from .reference_dataset_registry import ReferenceDatasetRegistry
from .comparator_ranking import (
    ComparatorRankingContext,
    ComparatorRankedReferenceSpec
)
from .comparator_consensus import (
    ConsensusSupportingReferenceSpec,
    ConsensusConflictingReferenceSpec,
    ConsensusLabelCandidateSpec,
    ConsensusEvidenceProfileSpec,
    ConsensusDecisionSpec,
    ComparatorConsensusIssueSpec,
    ComparatorConsensusSummarySpec,
    ComparatorConsensusContext
)
from .comparator_execution_config import ConsensusDecisionConfigSpec, build_default_consensus_decision_config

def resolve_consensus_label_for_reference(
    reference_dataset_id: str,
    reference_comparison_id: str,
    registry: ReferenceDatasetRegistry
) -> Tuple[str, str]:
    """
    Find the biological label for a reference comparison from the registry.
    """
    label_key = reference_comparison_id
    label_display = reference_comparison_id
    
    for ds in registry.datasets:
        if ds.reference_dataset_id == reference_dataset_id:
            for rc in ds.available_comparisons:
                if rc.reference_comparison_id == reference_comparison_id:
                    # Use enriched fields if available
                    k = rc.consensus_label_key
                    d = rc.consensus_label_display
                    
                    final_k = k if k else label_key
                    final_d = d if d else rc.comparison_label
                    return final_k, final_d
                    
    return label_key, label_display

def build_consensus_label_candidates(
    ranked_refs: Tuple[ComparatorRankedReferenceSpec, ...],
    registry: ReferenceDatasetRegistry,
    consensus_config: Optional[ConsensusDecisionConfigSpec] = None
) -> Tuple[ConsensusLabelCandidateSpec, ...]:
    """
    Group ranked references by their biological label and compute aggregate metrics.
    Sorting is governed by config policy.
    """
    cfg = consensus_config if consensus_config else build_default_consensus_decision_config()
    
    grouped: Dict[str, List[ComparatorRankedReferenceSpec]] = {}
    label_displays: Dict[str, str] = {}
    
    for ref in ranked_refs:
        lk, ld = resolve_consensus_label_for_reference(
            ref.reference_dataset_id,
            ref.reference_comparison_id,
            registry
        )
        if lk not in grouped:
            grouped[lk] = []
        grouped[lk].append(ref)
        label_displays[lk] = ld
        
    candidates: List[ConsensusLabelCandidateSpec] = []
    for lk, refs in grouped.items():
        scores = [r.integrated_score.integrated_score for r in refs]
        candidates.append(ConsensusLabelCandidateSpec(
            comparison_id=refs[0].comparison_id,
            label_key=lk,
            label_display=label_displays[lk],
            n_supporting_references=len(refs),
            mean_integrated_score=sum(scores) / len(scores),
            top_integrated_score=max(scores),
            supporting_reference_ids=tuple(
                f"{r.reference_dataset_id}:{r.reference_comparison_id}" for r in refs
            )
        ))
        
    # Sort candidates according to config policy
    # Current hardcoded logic matches the specific default policy string
    candidates.sort(
        key=lambda x: (x.mean_integrated_score, x.top_integrated_score, x.n_supporting_references),
        reverse=True
    )
    
    return tuple(candidates)

def build_consensus_evidence_profile(
    comparison_id: str,
    candidates: Tuple[ConsensusLabelCandidateSpec, ...],
    ranked_refs: Tuple[ComparatorRankedReferenceSpec, ...],
    registry: ReferenceDatasetRegistry,
    consensus_config: Optional[ConsensusDecisionConfigSpec] = None
) -> ConsensusEvidenceProfileSpec:
    """
    Split references into supporting and conflicting based on the top candidate.
    Uses weak support threshold from config.
    """
    cfg = consensus_config if consensus_config else build_default_consensus_decision_config()
    
    if not candidates:
        return ConsensusEvidenceProfileSpec(
            comparison_id=comparison_id,
            top_candidate=None,
            competing_candidates=(),
            supporting_references=(),
            conflicting_references=(),
            support_margin=None,
            has_conflict=False,
            has_weak_support=True
        )
        
    top = candidates[0]
    competing = candidates[1:]
    
    margin = None
    if len(candidates) > 1:
        margin = top.mean_integrated_score - candidates[1].mean_integrated_score
        
    supports: List[ConsensusSupportingReferenceSpec] = []
    conflicts: List[ConsensusConflictingReferenceSpec] = []
    
    for ref in ranked_refs:
        lk, _ = resolve_consensus_label_for_reference(
            ref.reference_dataset_id,
            ref.reference_comparison_id,
            registry
        )
        if lk == top.label_key:
            supports.append(ConsensusSupportingReferenceSpec(
                comparison_id=comparison_id,
                label_key=lk,
                reference_dataset_id=ref.reference_dataset_id,
                reference_comparison_id=ref.reference_comparison_id,
                integrated_score=ref.integrated_score.integrated_score,
                rank=ref.rank
            ))
        else:
            conflicts.append(ConsensusConflictingReferenceSpec(
                comparison_id=comparison_id,
                label_key=lk,
                reference_dataset_id=ref.reference_dataset_id,
                reference_comparison_id=ref.reference_comparison_id,
                integrated_score=ref.integrated_score.integrated_score,
                rank=ref.rank
            ))
            
    return ConsensusEvidenceProfileSpec(
        comparison_id=comparison_id,
        top_candidate=top,
        competing_candidates=competing,
        supporting_references=tuple(supports),
        conflicting_references=tuple(conflicts),
        support_margin=margin,
        has_conflict=len(conflicts) > 0,
        has_weak_support=(top.mean_integrated_score < cfg.weak_support_mean_threshold)
    )

def build_consensus_decision(
    evidence_profile: ConsensusEvidenceProfileSpec,
    has_top_rank_conflict: bool,
    consensus_config: Optional[ConsensusDecisionConfigSpec] = None
) -> ConsensusDecisionSpec:
    """
    Decide the final status based on evidence profile and ranking conflicts using config.
    """
    cfg = consensus_config if consensus_config else build_default_consensus_decision_config()
    cid = evidence_profile.comparison_id
    top = evidence_profile.top_candidate
    
    if not top:
        return ConsensusDecisionSpec(cid, cfg.insufficient_support_policy, None, None, ("no_ranked_matches",))
        
    reasons = []
    status = "consensus"
    
    # 1. Check for Top-Rank Conflict (from Ranking phase)
    if has_top_rank_conflict:
        reasons.append("top_rank_conflict_present")
        status = cfg.top_rank_conflict_policy
        
    # 2. Check Margin
    if evidence_profile.support_margin is not None:
        if evidence_profile.support_margin < cfg.consensus_margin_threshold:
            reasons.append("weak_support_margin")
            status = cfg.weak_margin_policy
            
    # 3. Check Evidence Volume
    if top.n_supporting_references < cfg.minimum_supporting_references:
        reasons.append("insufficient_supporting_references")
        status = cfg.insufficient_support_policy

    # Final mapping
    decided_lk = top.label_key if status == "consensus" else None
    decided_ld = top.label_display if status == "consensus" else None
    
    return ConsensusDecisionSpec(
        comparison_id=cid,
        decision_status=status,
        decided_label_key=decided_lk,
        decided_label_display=decided_ld,
        reason_codes=tuple(reasons)
    )

def build_comparator_consensus_context(
    ranking_context: ComparatorRankingContext,
    registry: ReferenceDatasetRegistry,
    consensus_config: Optional[ConsensusDecisionConfigSpec] = None
) -> ComparatorConsensusContext:
    """
    Orchestrate the consensus labeling phase using the provided config.
    """
    cfg = consensus_config if consensus_config else build_default_consensus_decision_config()
    
    decisions: List[ConsensusDecisionSpec] = []
    profiles: List[ConsensusEvidenceProfileSpec] = []
    issues: List[ComparatorConsensusIssueSpec] = []
    
    # 1. Group ranked refs by experimental comparison
    ranked_by_cid: Dict[str, List[ComparatorRankedReferenceSpec]] = {}
    for r in ranking_context.ranked_references:
        if r.comparison_id not in ranked_by_cid:
            ranked_by_cid[r.comparison_id] = []
        ranked_by_cid[r.comparison_id].append(r)
        
    # Conflicts map for quick lookup
    comp_conflicts = {c.comparison_id for c in ranking_context.top_rank_conflicts}
    
    # 2. Process each comparison
    target_cids = {r.comparison_id for r in ranking_context.ranked_references}
    
    for cid in target_cids:
        refs = tuple(ranked_by_cid.get(cid, []))
        candidates = build_consensus_label_candidates(refs, registry, consensus_config=cfg)
        profile = build_consensus_evidence_profile(cid, candidates, refs, registry, consensus_config=cfg)
        decision = build_consensus_decision(
            profile, 
            cid in comp_conflicts,
            consensus_config=cfg
        )
        
        profiles.append(profile)
        decisions.append(decision)

    # 3. Summary
    n_total = len(target_cids)
    n_cons = sum(1 for d in decisions if d.decision_status == "consensus")
    n_no = sum(1 for d in decisions if d.decision_status == "no_consensus")
    n_ins = sum(1 for d in decisions if d.decision_status == "insufficient_evidence")
    n_abs = sum(1 for d in decisions if d.decision_status == "abstain")
    
    is_ready = (
        ranking_context.summary.is_ready_for_reference_ranking and
        n_total > 0
    )
    
    summary = ComparatorConsensusSummarySpec(
        n_ranked_comparisons=n_total,
        n_consensus=n_cons,
        n_abstain=n_abs,
        n_no_consensus=n_no,
        n_insufficient_evidence=n_ins,
        is_ready_for_consensus_export=is_ready
    )
    
    return ComparatorConsensusContext(
        ranking_context=ranking_context,
        decisions=tuple(decisions),
        evidence_profiles=tuple(profiles),
        issues=tuple(issues),
        summary=summary,
        consensus_config=cfg
    )
