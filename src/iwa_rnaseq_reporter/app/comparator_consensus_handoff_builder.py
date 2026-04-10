import json
import dataclasses
from typing import Tuple
from .comparator_consensus import ComparatorConsensusContext
from .comparator_consensus_export import ComparatorConsensusExportPayload
from .comparator_consensus_handoff import (
    ComparatorConsensusBundleRefSpec,
    ComparatorConsensusComparisonRefSpec,
    ComparatorConsensusHandoffPayload
)

def build_consensus_handoff_payload(
    context: ComparatorConsensusContext,
    export_payload: ComparatorConsensusExportPayload,
    bundle_filename: str
) -> ComparatorConsensusHandoffPayload:
    """
    Construct the final handoff contract for downstream integration.
    """
    # 1. Build Bundle References (Relative Paths)
    bundle_refs = ComparatorConsensusBundleRefSpec(
        consensus_bundle_filename=bundle_filename,
        consensus_manifest_path="consensus_manifest.json",
        consensus_summary_path="consensus_summary.json",
        consensus_decisions_path="consensus_decisions.json",
        evidence_profiles_path="evidence_profiles.json",
        consensus_handoff_contract_path="consensus_handoff_contract.json"
    )
    
    # 2. Extract uniquely decided labels
    decided_labels = sorted(list(set(
        d.decided_label_key for d in context.decisions 
        if d.decision_status == "consensus" and d.decided_label_key
    )))
    
    # 3. Build Comparison Refs
    comparison_refs = [
        ComparatorConsensusComparisonRefSpec(
            comparison_id=d.comparison_id,
            decision_status=d.decision_status,
            decided_label_key=d.decided_label_key,
            decided_label_display=d.decided_label_display
        )
        for d in context.decisions
    ]
    
    return ComparatorConsensusHandoffPayload(
        consensus_run_id=export_payload.manifest.consensus_run_id,
        bundle_refs=bundle_refs,
        included_comparison_ids=tuple(d.comparison_id for d in context.decisions),
        decided_label_keys=tuple(decided_labels),
        comparison_decision_refs=tuple(comparison_refs),
        summary=context.summary
    )

def serialize_handoff_contract(payload: ComparatorConsensusHandoffPayload) -> str:
    """
    Helper to serialize the handoff payload to a pretty-printed JSON string.
    """
    return json.dumps(dataclasses.asdict(payload), indent=2, ensure_ascii=False)
