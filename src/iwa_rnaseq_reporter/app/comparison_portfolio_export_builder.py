import io
import json
import zipfile
from dataclasses import asdict
from typing import List, Optional
from iwa_rnaseq_reporter.app.comparison_portfolio_context import ComparisonPortfolioContext
from iwa_rnaseq_reporter.app.deg_export_bundle import build_deg_report_summary_md
from .comparison_portfolio_export import (
    ComparisonPortfolioManifestSpec,
    ComparisonPortfolioIndexEntrySpec,
    ComparisonPortfolioExportPayload
)
from .comparison_portfolio_handoff_builder import build_comparison_portfolio_handoff_payload

def build_comparison_portfolio_manifest(portfolio: ComparisonPortfolioContext) -> ComparisonPortfolioManifestSpec:
    """
    Build the portfolio manifest from the current context.
    """
    return ComparisonPortfolioManifestSpec(
        portfolio_id=portfolio.portfolio_id,
        n_comparisons=portfolio.count,
        included_comparison_ids=portfolio.comparison_ids
    )

def build_comparison_portfolio_index(portfolio: ComparisonPortfolioContext) -> List[ComparisonPortfolioIndexEntrySpec]:
    """
    Build the index of comparisons contained within the portfolio.
    """
    entries = []
    for record in portfolio.records:
        m = record.summary_metrics
        entries.append(ComparisonPortfolioIndexEntrySpec(
            comparison_id=record.comparison_id,
            comparison_label=record.comparison_label,
            matrix_kind=record.export_payload.metadata.matrix_kind,
            n_features_tested=m.n_features_tested,
            n_sig_up=m.n_sig_up,
            n_sig_down=m.n_sig_down,
            max_abs_log2_fc=m.max_abs_log2_fc,
            bundle_filename=record.bundle_filename
        ))
    return entries

def build_comparison_portfolio_export_payload(portfolio: ComparisonPortfolioContext) -> ComparisonPortfolioExportPayload:
    """
    Consolidate all data for portfolio export in a single payload.
    """
    if portfolio.count == 0:
        raise ValueError("Cannot build export payload for an empty portfolio.")
        
    return ComparisonPortfolioExportPayload(
        manifest=build_comparison_portfolio_manifest(portfolio),
        comparison_index=build_comparison_portfolio_index(portfolio)
    )

def build_comparison_portfolio_bundle_filename(portfolio: ComparisonPortfolioContext) -> str:
    """
    Generate a deterministic filename for the portfolio bundle.
    """
    return f"portfolio_{portfolio.portfolio_id}_{portfolio.count}comparisons.zip"

def build_comparison_portfolio_export_bundle(portfolio: ComparisonPortfolioContext) -> bytes:
    """
    Generate a ZIP archive containing the entire portfolio orchestrated for downstream.
    """
    payload = build_comparison_portfolio_export_payload(portfolio)

    # Generate portfolio handoff contract
    handoff_contract = build_comparison_portfolio_handoff_payload(
        portfolio, payload, build_comparison_portfolio_bundle_filename(portfolio)
    )
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Top-level Metadata
        zf.writestr(
            "portfolio_manifest.json",
            json.dumps(asdict(payload.manifest), indent=2, ensure_ascii=False)
        )
        zf.writestr(
            "comparison_index.json",
            json.dumps([asdict(e) for e in payload.comparison_index], indent=2, ensure_ascii=False)
        )
        zf.writestr(
            "portfolio_handoff_contract.json",
            json.dumps(handoff_contract.to_dict(), indent=2, ensure_ascii=False)
        )
        
        # 2. Comparison Subdirectories
        for record in portfolio.records:
            cid = record.comparison_id
            base_path = f"comparisons/{cid}"
            
            exp = record.export_payload
            
            # - handoff_contract.json
            zf.writestr(
                f"{base_path}/handoff_contract.json",
                json.dumps(record.handoff_payload.to_dict(), indent=2, ensure_ascii=False)
            )
            # - comparison_summary.json
            zf.writestr(
                f"{base_path}/comparison_summary.json",
                json.dumps(exp.summary.to_dict(), indent=2, ensure_ascii=False)
            )
            # - summary_metrics.json
            zf.writestr(
                f"{base_path}/summary_metrics.json",
                json.dumps(asdict(exp.summary_metrics), indent=2, ensure_ascii=False)
            )
            # - run_metadata.json
            zf.writestr(
                f"{base_path}/run_metadata.json",
                json.dumps(exp.metadata.to_dict(), indent=2, ensure_ascii=False)
            )
            # - report_summary.md
            zf.writestr(
                f"{base_path}/report_summary.md",
                build_deg_report_summary_md(exp)
            )
            
    return buf.getvalue()
