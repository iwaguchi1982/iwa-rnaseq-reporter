from typing import Optional, Tuple, Iterable, Dict
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ComparatorConsensusContext
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff import ComparatorConsensusBundleRefSpec
from iwa_rnaseq_reporter.app.comparator_decision_support import (
    DecisionArtifactRefSpec,
    DecisionEvidenceStatsSpec,
    DecisionTopReferenceRefSpec,
    DecisionEvidenceRefSpec,
    ComparatorDecisionSupportSummarySpec,
    ComparatorDecisionSupportPayload
)

DEFAULT_MAX_TOP_REFS = 3

def build_decision_artifact_refs(bundle_refs: ComparatorConsensusBundleRefSpec) -> DecisionArtifactRefSpec:
    """
    Construct artifact pointers using existing bundle references.
    Corresponds to spec 6.1.
    """
    return DecisionArtifactRefSpec(
        consensus_manifest_path=bundle_refs.consensus_manifest_path,
        consensus_handoff_contract_path=bundle_refs.consensus_handoff_contract_path,
        consensus_decisions_json_path=bundle_refs.consensus_decisions_path,
        evidence_profiles_json_path=bundle_refs.evidence_profiles_path,
        consensus_decisions_csv_path="consensus_decisions.csv",
        report_summary_md_path="report_summary.md"
    )

def build_decision_evidence_stats(profile: Optional[ConsensusEvidenceProfileSpec]) -> DecisionEvidenceStatsSpec:
    """
    Extract summary statistics from an evidence profile.
    Uses defensive fallbacks if profile is missing.
    Corresponds to spec 6.2.
    """
    if not profile:
        return DecisionEvidenceStatsSpec(
            support_margin=None,
            has_conflict=False,
            has_weak_support=True,
            n_supporting_references=0,
            n_conflicting_references=0,
            n_competing_candidates=0
        )
    
    return DecisionEvidenceStatsSpec(
        support_margin=profile.support_margin,
        has_conflict=profile.has_conflict,
        has_weak_support=profile.has_weak_support,
        n_supporting_references=len(profile.supporting_references),
        n_conflicting_references=len(profile.conflicting_references),
        n_competing_candidates=len(profile.competing_candidates)
    )

def _extract_integrated_score(ref: any) -> Optional[float]:
    """
    Defensively extract the integrated score from various reference types.
    Handles both direct float field (v0.19.4) and nested object field (v0.19.3).
    """
    val = getattr(ref, 'integrated_score', None)
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Fallback for nested object structure
    return getattr(val, 'integrated_score', 0.0)

def build_top_reference_refs(
    refs: Iterable, 
    max_refs: int = DEFAULT_MAX_TOP_REFS
) -> Tuple[DecisionTopReferenceRefSpec, ...]:
    """
    Select and format top-tier evidence references.
    Sorted by integrated_score desc, then rank asc.
    Corresponds to spec 6.3.
    """
    # Defensive sorting: score desc, then rank asc
    sorted_refs = sorted(
        refs, 
        key=lambda r: (-(_extract_integrated_score(r)), (r.rank or 999), r.reference_dataset_id, r.reference_comparison_id)
    )
    
    selected = sorted_refs[:max_refs]
    
    return tuple(
        DecisionTopReferenceRefSpec(
            reference_dataset_id=r.reference_dataset_id,
            reference_comparison_id=r.reference_comparison_id,
            label_key=getattr(r, 'label_key', None),
            label_display=getattr(r, 'label_display', None),
            integrated_score=_extract_integrated_score(r),
            rank=r.rank
        )
        for r in selected
    )

def build_decision_evidence_ref(
    decision: ConsensusDecisionSpec,
    profile: Optional[ConsensusEvidenceProfileSpec],
    artifact_refs: DecisionArtifactRefSpec,
    max_top_refs: int = DEFAULT_MAX_TOP_REFS
) -> DecisionEvidenceRefSpec:
    """
    Assemble a compact decision support record for a single comparison.
    Corresponds to spec 6.4.
    """
    stats = build_decision_evidence_stats(profile)
    
    supporting_refs = ()
    conflicting_refs = ()
    
    if profile:
        supporting_refs = build_top_reference_refs(profile.supporting_references, max_top_refs)
        conflicting_refs = build_top_reference_refs(profile.conflicting_references, max_top_refs)
        
    return DecisionEvidenceRefSpec(
        comparison_id=decision.comparison_id,
        decision_status=decision.decision_status,
        decided_label_key=decision.decided_label_key,
        decided_label_display=decision.decided_label_display,
        reason_codes=decision.reason_codes,
        evidence_stats=stats,
        artifact_refs=artifact_refs,
        top_supporting_reference_refs=supporting_refs,
        top_conflicting_reference_refs=conflicting_refs
    )

def build_decision_support_summary(
    decision_refs: Tuple[DecisionEvidenceRefSpec, ...]
) -> ComparatorDecisionSupportSummarySpec:
    """
    Aggregate metrics for the decision support payload block.
    Corresponds to spec 6.5.
    """
    counts = {
        "consensus": 0,
        "abstain": 0,
        "no_consensus": 0,
        "insufficient_evidence": 0
    }
    
    for r in decision_refs:
        status = r.decision_status
        if status in counts:
            counts[status] += 1
            
    return ComparatorDecisionSupportSummarySpec(
        n_decision_refs=len(decision_refs),
        n_consensus=counts["consensus"],
        n_abstain=counts["abstain"],
        n_no_consensus=counts["no_consensus"],
        n_insufficient_evidence=counts["insufficient_evidence"]
    )

def build_decision_support_payload(
    context: ComparatorConsensusContext,
    bundle_refs: ComparatorConsensusBundleRefSpec,
    max_top_refs: int = DEFAULT_MAX_TOP_REFS
) -> ComparatorDecisionSupportPayload:
    """
    High-level orchestrator for the decision support payload.
    Corresponds to spec 6.6.
    """
    # 1. Map profiles by comparison_id for efficient join
    profile_map: Dict[str, ConsensusEvidenceProfileSpec] = {
        p.comparison_id: p for p in context.evidence_profiles
    }
    
    # 2. Shared artifact refs
    art_refs = build_decision_artifact_refs(bundle_refs)
    
    # 3. Build individual refs
    decision_refs = tuple(
        build_decision_evidence_ref(d, profile_map.get(d.comparison_id), art_refs, max_top_refs)
        for d in context.decisions
    )
    
    # 4. Aggregate summary
    summary = build_decision_support_summary(decision_refs)
    
    return ComparatorDecisionSupportPayload(
        decision_evidence_refs=decision_refs,
        summary=summary
    )
