import datetime
import json
import io
import zipfile
import pandas as pd
from typing import Tuple, List, Optional
from .comparator_consensus import ComparatorConsensusContext
from .comparator_consensus_export import (
    ComparatorConsensusManifestSpec,
    ComparatorConsensusDecisionRowSpec,
    ComparatorConsensusExportPayload,
    ProvenanceSpec
)
from .version_helper import get_package_version

def build_consensus_run_id() -> str:
    """
    Generate a deterministic-ish run ID for the consensus phase.
    """
    now = datetime.datetime.now()
    return f"consensus_{now.strftime('%Y%m%d_%H%M%S')}"

def build_consensus_decision_rows(
    context: ComparatorConsensusContext
) -> Tuple[ComparatorConsensusDecisionRowSpec, ...]:
    """
    Flatten consensus decisions into tabular rows.
    """
    profile_map = {p.comparison_id: p for p in context.evidence_profiles}
    rows: List[ComparatorConsensusDecisionRowSpec] = []
    
    for dec in context.decisions:
        prof = profile_map.get(dec.comparison_id)
        rows.append(ComparatorConsensusDecisionRowSpec(
            comparison_id=dec.comparison_id,
            decision_status=dec.decision_status,
            decided_label_key=dec.decided_label_key,
            decided_label_display=dec.decided_label_display,
            support_margin=prof.support_margin if prof else None,
            has_conflict=prof.has_conflict if prof else False,
            has_weak_support=prof.has_weak_support if prof else True
        ))
    return tuple(rows)

def build_consensus_export_payload(
    context: ComparatorConsensusContext,
    run_id: str,
    generated_at: Optional[str] = None
) -> ComparatorConsensusExportPayload:
    """
    Gather all data needed for serialization into the bundle.
    """
    # v0.19.1/v0.19.2 Provenance
    gen_at = generated_at
    if gen_at is None:
        now = datetime.datetime.now(datetime.timezone.utc)
        gen_at = now.isoformat()
        
    prov = ProvenanceSpec(
        producer_app="iwa_rnaseq_reporter",
        producer_version=get_package_version(),
        source_consensus_run_id=run_id
    )

    manifest = ComparatorConsensusManifestSpec(
        consensus_run_id=run_id,
        n_ranked_comparisons=context.summary.n_ranked_comparisons,
        n_consensus=context.summary.n_consensus,
        n_abstain=context.summary.n_abstain,
        n_no_consensus=context.summary.n_no_consensus,
        n_insufficient_evidence=context.summary.n_insufficient_evidence,
        generated_at=gen_at,
        provenance=prov
    )
    
    return ComparatorConsensusExportPayload(
        manifest=manifest,
        decision_rows=build_consensus_decision_rows(context),
        decisions=context.decisions,
        evidence_profiles=context.evidence_profiles,
        issues=context.issues,
        summary=context.summary
    )

def build_consensus_report_summary_md(
    payload: ComparatorConsensusExportPayload
) -> str:
    """
    Generate a human-readable Markdown summary for the bundle.
    """
    sum_spec = payload.summary
    lines = [
        f"# RNA-Seq Consensus Report Summary",
        f"Run ID: `{payload.manifest.consensus_run_id}`",
        f"",
        f"## Execution Summary",
        f"- Total Comparisons Processed: {sum_spec.n_ranked_comparisons}",
        f"- Clear Consensus Reached: **{sum_spec.n_consensus}**",
        f"- No Consensus (Conflicts/Near-ties): {sum_spec.n_no_consensus}",
        f"- Insufficient Evidence: {sum_spec.n_insufficient_evidence}",
        f"",
        f"## Decision Details",
        f"| Comparison ID | Status | Decided Label | Margin |",
        f"| :--- | :--- | :--- | :--- |"
    ]
    
    for row in payload.decision_rows:
        label = row.decided_label_display if row.decided_label_display else "-"
        margin = f"{row.support_margin:.3f}" if row.support_margin is not None else "-"
        lines.append(f"| {row.comparison_id} | `{row.decision_status}` | {label} | {margin} |")
        
    # v0.19.1 Provenance Section
    lines.extend([
        f"",
        f"---",
        f"**Data Provenance**",
        f"- Schema Version: `{payload.manifest.schema_version}`",
        f"- Generated At: {payload.manifest.generated_at}",
        f"- Producer: `{payload.manifest.provenance.producer_app} (v{payload.manifest.provenance.producer_version})`",
        f"- Consensus Run ID: `{payload.manifest.provenance.source_consensus_run_id}`"
    ])
        
    return "\n".join(lines)

def build_consensus_export_bundle(
    payload: ComparatorConsensusExportPayload,
    handoff_json: str
) -> bytes:
    """
    Create a ZIP bundle containing all consensus results.
    """
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # JSON manifests and data
        # Note: In real app, we'd use a robust dataclass-to-dict serializer.
        # For now, we assume standard library json handles simple dataclasses or we convert them.
        
        def write_json(name, data):
            # Simple conversion for dataclasses
            if hasattr(data, "__dict__"): # or use asdict if imports allow
                import dataclasses
                d = dataclasses.asdict(data)
            elif isinstance(data, (list, tuple)):
                import dataclasses
                d = [dataclasses.asdict(x) if dataclasses.is_dataclass(x) else x for x in data]
            else:
                d = data
            zf.writestr(name, json.dumps(d, indent=2, ensure_ascii=False))

        write_json("consensus_manifest.json", payload.manifest)
        write_json("consensus_summary.json", payload.summary)
        write_json("consensus_decisions.json", payload.decisions)
        write_json("evidence_profiles.json", payload.evidence_profiles)
        write_json("consensus_issues.json", payload.issues)
        
        # Handoff Contract
        zf.writestr("consensus_handoff_contract.json", handoff_json)
        
        # CSV Table
        df = pd.DataFrame([vars(r) for r in payload.decision_rows])
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        zf.writestr("consensus_decisions.csv", csv_buf.getvalue())
        
        # Markdown Summary
        zf.writestr("report_summary.md", build_consensus_report_summary_md(payload))
        
    return buf.getvalue()
