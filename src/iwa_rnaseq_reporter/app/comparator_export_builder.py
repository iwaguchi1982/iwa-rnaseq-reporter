import io
import json
import zipfile
import pandas as pd
from datetime import datetime
from dataclasses import asdict
from typing import Tuple
from .comparator_engine import ComparatorResultContext
from .comparator_export import (
    ComparatorExportManifestSpec,
    ComparatorExportMatchRowSpec,
    ComparatorExportPayload
)
from .comparator_handoff_builder import build_comparator_handoff_payload

def build_comparator_run_id(portfolio_id: str) -> str:
    """
    Generate a deterministic-ish run ID for the comparison session.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"comp-run-{portfolio_id}-{timestamp}"

def build_comparator_export_payload(
    result_context: ComparatorResultContext,
    run_id: str
) -> ComparatorExportPayload:
    """
    Consolidate calculation results into a flat export payload.
    """
    summary = result_context.summary
    portfolio_id = result_context.matching_context.summary.portfolio_id
    
    manifest = ComparatorExportManifestSpec(
        comparator_run_id=run_id,
        portfolio_id=portfolio_id,
        n_total_matches_requested=summary.n_total_matches_requested,
        n_successful_matches=summary.n_successful_matches,
        n_skipped_matches=summary.n_skipped_matches
    )
    
    match_rows = []
    for res in result_context.match_results:
        s = res.score
        match_rows.append(ComparatorExportMatchRowSpec(
            comparison_id=res.comparison_id,
            reference_dataset_id=res.reference_dataset_id,
            reference_comparison_id=res.reference_comparison_id,
            n_overlap_features=s.n_overlap_features,
            n_top_n_overlap_features=s.n_top_n_overlap_features,
            direction_concordance=s.direction_concordance,
            signed_effect_correlation=s.signed_effect_correlation
        ))
        
    return ComparatorExportPayload(
        manifest=manifest,
        match_rows=tuple(match_rows),
        skipped_matches=result_context.skipped_matches,
        issues=result_context.issues,
        summary=summary
    )

def build_comparator_bundle_filename(run_id: str) -> str:
    """
    Generate the filename for the comparator result bundle.
    """
    return f"{run_id}.zip"

def build_comparator_report_summary_md(payload: ComparatorExportPayload) -> str:
    """
    Generate a concise human-readable summary of the comparison results.
    """
    m = payload.manifest
    md = [
        f"# Comparator Execution Summary: {m.comparator_run_id}",
        "",
        f"- **Portfolio ID**: {m.portfolio_id}",
        f"- **Total Matches Requested**: {m.n_total_matches_requested}",
        f"- **Successful Matches**: {m.n_successful_matches}",
        f"- **Skipped Matches**: {m.n_skipped_matches}",
        "",
        "## Top Matches (by absolute correlation)",
        ""
    ]
    
    # Sort and take top 5 for summary
    sorted_rows = sorted(
        [r for r in payload.match_rows if r.signed_effect_correlation is not None],
        key=lambda x: abs(x.signed_effect_correlation or 0),
        reverse=True
    )[:5]
    
    if sorted_rows:
        md.append("| Comparison | Reference | Correlation | Concordance |")
        md.append("|------------|-----------|-------------|-------------|")
        for r in sorted_rows:
            corr = f"{r.signed_effect_correlation:.3f}" if r.signed_effect_correlation is not None else "N/A"
            conc = f"{r.direction_concordance:.3f}" if r.direction_concordance is not None else "N/A"
            md.append(f"| {r.comparison_id} | {r.reference_comparison_id} | {corr} | {conc} |")
    else:
        md.append("*No successful matches with valid correlation found.*")
        
    return "\n".join(md)

def build_comparator_export_bundle(result_context: ComparatorResultContext) -> bytes:
    """
    Orchestrate the creation of a full results ZIP bundle.
    """
    pid = result_context.matching_context.summary.portfolio_id
    run_id = build_comparator_run_id(pid)
    filename = build_comparator_bundle_filename(run_id)
    
    payload = build_comparator_export_payload(result_context, run_id)
    handoff = build_comparator_handoff_payload(result_context, payload, filename)
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Identity & Summary
        zf.writestr("comparator_manifest.json", json.dumps(asdict(payload.manifest), indent=2))
        zf.writestr("comparator_summary.json", json.dumps(asdict(payload.summary), indent=2))
        zf.writestr("comparator_handoff_contract.json", json.dumps(handoff.to_dict(), indent=2))
        
        # 2. Detailed Result JSONs
        zf.writestr("match_results.json", json.dumps([asdict(r) for r in payload.match_rows], indent=2))
        zf.writestr("skipped_matches.json", json.dumps([asdict(s) for s in payload.skipped_matches], indent=2))
        zf.writestr("engine_issues.json", json.dumps([asdict(i) for i in payload.issues], indent=2))
        
        # 3. Flat CSV (Recommended)
        if payload.match_rows:
            df = pd.DataFrame([asdict(r) for r in payload.match_rows])
            zf.writestr("match_results.csv", df.to_csv(index=False))
            
        # 4. Human-readable Summary
        zf.writestr("report_summary.md", build_comparator_report_summary_md(payload))
        
    return buf.getvalue()
