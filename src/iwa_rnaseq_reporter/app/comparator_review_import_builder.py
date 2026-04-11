import io
import json
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from .comparator_review_export import (
    ComparatorReviewExportManifestSpec,
    ComparatorReviewExportRowSpec,
    ComparatorReviewSummarySpec
)
from .comparator_review_handoff import (
    ComparatorReviewHandoffPayload,
    ComparatorReviewBundleRefSpec,
    ComparatorReviewSourceRefSpec,
    ComparatorReviewDecisionRefSpec
)
from .comparator_review_import import (
    ComparatorReviewImportContext,
    ComparatorReviewImportPaths
)

def read_review_bundle(bundle_path: str) -> ComparatorReviewImportContext:
    """Read and validate a review bundle ZIP archive."""
    issues = []
    
    try:
        with zipfile.ZipFile(bundle_path, "r") as zf:
            namelist = zf.namelist()
            
            # 1. Existence Checks
            required = [
                "review_manifest.json",
                "review_rows.json",
                "review_summary.json",
                "review_handoff_contract.json",
                "review_summary.md"
            ]
            for r in required:
                if r not in namelist:
                    issues.append(f"Missing required file: {r}")
            
            if issues:
                return _build_error_ctx(issues)
                
            # 2. Parse Manifest
            manifest_json = json.loads(zf.read("review_manifest.json"))
            manifest = ComparatorReviewExportManifestSpec(**manifest_json)
            
            # 3. Parse Summary
            summary_json = json.loads(zf.read("review_summary.json"))
            summary = ComparatorReviewSummarySpec(**summary_json)
            
            # 4. Parse Rows
            rows_data = json.loads(zf.read("review_rows.json"))
            rows = tuple(ComparatorReviewExportRowSpec(**r) for r in rows_data)
            
            # 5. Parse Handoff Contract
            handoff_data = json.loads(zf.read("review_handoff_contract.json"))
            
            # Nested dataclass parsing for Handoff
            b_refs_data = handoff_data.pop("bundle_refs")
            b_refs = ComparatorReviewBundleRefSpec(**b_refs_data)
            
            s_refs_data = handoff_data.pop("source_refs")
            s_refs = ComparatorReviewSourceRefSpec(**s_refs_data)
            
            d_refs_data = handoff_data.pop("review_decision_refs")
            d_refs = tuple(ComparatorReviewDecisionRefSpec(**d) for d in d_refs_data)
            
            h_summary_data = handoff_data.pop("summary")
            h_summary = ComparatorReviewSummarySpec(**h_summary_data)
            
            handoff_contract = ComparatorReviewHandoffPayload(
                **handoff_data,
                bundle_refs=b_refs,
                source_refs=s_refs,
                review_decision_refs=d_refs,
                summary=h_summary
            )
            
            # 6. Metadata Validation
            if manifest.source_consensus_run_id != handoff_contract.source_consensus_run_id:
                issues.append("Mismatch in source_consensus_run_id between manifest and handoff.")
            
            if len(rows) != summary.n_total_rows:
                issues.append(f"Row count mismatch: {len(rows)} rows found, summary expects {summary.n_total_rows}.")
                
            # 7. Build Paths
            paths = ComparatorReviewImportPaths(
                manifest="review_manifest.json",
                handoff_contract="review_handoff_contract.json",
                rows_json="review_rows.json",
                rows_csv="review_rows.csv",
                summary_json="review_summary.json",
                summary_md="review_summary.md"
            )
            
            return ComparatorReviewImportContext(
                manifest=manifest,
                handoff_contract=handoff_contract,
                review_rows=rows,
                summary=summary,
                summary_md=zf.read("review_summary.md").decode("utf-8"),
                paths=paths,
                provenance=manifest.provenance,
                issues=tuple(issues)
            )
            
    except Exception as e:
        return _build_error_ctx([f"Failed to read ZIP: {e}"])

def _build_error_ctx(issues: List[str]) -> ComparatorReviewImportContext:
    """Helper to return an island context in case of fatal load errors."""
    return ComparatorReviewImportContext(
        manifest=None,
        handoff_contract=None,
        review_rows=(),
        summary=None,
        summary_md="",
        paths=None,
        issues=tuple(issues)
    )
