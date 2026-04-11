import io
import json
import zipfile
from typing import Dict, Any, List, Optional, Tuple, Set
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
    """Read and strictly validate a review bundle ZIP archive."""
    issues = []
    
    try:
        with zipfile.ZipFile(bundle_path, "r") as zf:
            namelist = zf.namelist()
            
            # 1. Required Artifact Existence (spec 165-173)
            required = [
                "review_manifest.json",
                "review_rows.json",
                "review_rows.csv",
                "review_summary.json",
                "review_summary.md",
                "review_handoff_contract.json"
            ]
            for r in required:
                if r not in namelist:
                    issues.append(f"Missing required artifact: {r}")
            
            if "review_manifest.json" not in namelist or "review_handoff_contract.json" not in namelist:
                return _build_error_ctx(issues)
                
            # 2. Parse and Validate Schema (spec 175-189, 46-71 hardening)
            manifest_json = json.loads(zf.read("review_manifest.json"))
            if manifest_json.get("schema_name") != "comparator-review-export-manifest":
                issues.append(f"Invalid manifest schema_name: {manifest_json.get('schema_name')}")
            if manifest_json.get("schema_version") != "1.0.0":
                issues.append(f"Invalid manifest schema_version: {manifest_json.get('schema_version')}")
            if not isinstance(manifest_json.get("provenance"), dict):
                issues.append("Manifest provenance must be a dictionary.")
            
            manifest = ComparatorReviewExportManifestSpec(**manifest_json)
            
            handoff_data = json.loads(zf.read("review_handoff_contract.json"))
            if handoff_data.get("schema_name") != "comparator-review-handoff":
                issues.append(f"Invalid handoff schema_name: {handoff_data.get('schema_name')}")
            if handoff_data.get("schema_version") != "1.0.0":
                issues.append(f"Invalid handoff schema_version: {handoff_data.get('schema_version')}")
            if not isinstance(handoff_data.get("provenance"), dict):
                issues.append("Handoff provenance must be a dictionary.")

            # 3. Source Consistency (spec 190-192)
            if manifest.source_consensus_run_id != handoff_data.get("source_consensus_run_id"):
                issues.append("Consensus Run ID mismatch between manifest and handoff contract.")

            # Nested dataclass parsing for Handoff
            b_refs_data = handoff_data.get("bundle_refs", {}) or {}
            b_refs = ComparatorReviewBundleRefSpec(**b_refs_data)
            
            s_refs_data = handoff_data.get("source_refs", {}) or {}
            s_refs = ComparatorReviewSourceRefSpec(**s_refs_data)
            
            d_refs_data = handoff_data.get("review_decision_refs", []) or []
            d_refs = tuple(ComparatorReviewDecisionRefSpec(**d) for d in d_refs_data)
            
            h_summary_data = handoff_data.get("summary", {}) or {}
            # Ensure required fields for SummarySpec are present to avoid TypeError
            if h_summary_data:
                h_summary = ComparatorReviewSummarySpec(
                    n_total_rows=h_summary_data.get("n_total_rows", 0),
                    n_annotated_rows=h_summary_data.get("n_annotated_rows", 0),
                    n_unreviewed=h_summary_data.get("n_unreviewed", 0),
                    n_flagged=h_summary_data.get("n_flagged", 0),
                    n_reviewed=h_summary_data.get("n_reviewed", 0),
                    n_handoff_candidate=h_summary_data.get("n_handoff_candidate", 0),
                    n_high_priority=h_summary_data.get("n_high_priority", 0),
                    n_follow_up_required=h_summary_data.get("n_follow_up_required", 0),
                    decision_status_counts=h_summary_data.get("decision_status_counts", {}),
                    triage_status_counts=h_summary_data.get("triage_status_counts", {})
                )
            else:
                h_summary = None
            
            # Remaining top-level fields
            exclude_keys = ["bundle_refs", "source_refs", "review_decision_refs", "summary", "included_comparison_ids"]
            h_payload_data = {k: v for k, v in handoff_data.items() if k not in exclude_keys}
            
            handoff_contract = ComparatorReviewHandoffPayload(
                **h_payload_data,
                included_comparison_ids=tuple(handoff_data.get("included_comparison_ids", [])),
                bundle_refs=b_refs,
                source_refs=s_refs,
                review_decision_refs=d_refs,
                summary=h_summary
            )
            
            # 4. Content Parsing (Moved earlier to allow cross-validation)
            # Use zf.open() or check namelist before read to avoid KeyErrors
            summary = None
            if "review_summary.json" in namelist:
                try:
                    summary_data = json.loads(zf.read("review_summary.json"))
                    summary = ComparatorReviewSummarySpec(
                        n_total_rows=summary_data.get("n_total_rows", 0),
                        n_annotated_rows=summary_data.get("n_annotated_rows", 0),
                        n_unreviewed=summary_data.get("n_unreviewed", 0),
                        n_flagged=summary_data.get("n_flagged", 0),
                        n_reviewed=summary_data.get("n_reviewed", 0),
                        n_handoff_candidate=summary_data.get("n_handoff_candidate", 0),
                        n_high_priority=summary_data.get("n_high_priority", 0),
                        n_follow_up_required=summary_data.get("n_follow_up_required", 0),
                        decision_status_counts=summary_data.get("decision_status_counts", {}),
                        triage_status_counts=summary_data.get("triage_status_counts", {})
                    )
                except Exception as e:
                    issues.append(f"Broken summary JSON structure: {e}")

            rows = ()
            if "review_rows.json" in namelist:
                rows_data = json.loads(zf.read("review_rows.json"))
                rows = tuple(ComparatorReviewExportRowSpec(**r) for r in rows_data)
            
            summary_md = ""
            if "review_summary.md" in namelist:
                summary_md = zf.read("review_summary.md").decode("utf-8")

            # 5. ID Consistency & Summary Integrity (spec 194-216: now with safe defaults)
            row_ids = [r.comparison_id for r in rows]
            if len(row_ids) != len(set(row_ids)):
                issues.append("Duplicate comparison_ids found in review rows.")
                
            inc_ids = handoff_contract.included_comparison_ids if handoff_contract else ()
            if handoff_contract and len(inc_ids) != len(d_refs):
                issues.append("Handoff included_comparison_ids count mismatch.")
            
            if handoff_contract and set(row_ids) != set(inc_ids):
                issues.append("Set of comparison_ids in rows does not match handoff contract.")
                
            if summary and len(rows) != summary.n_total_rows:
                issues.append(f"Row count ({len(rows)}) mismatch with summary total ({summary.n_total_rows}).")
            
            if handoff_contract and handoff_contract.summary and len(rows) != handoff_contract.summary.n_total_rows:
                issues.append(f"Row count ({len(rows)}) mismatch with handoff summary.")

            # 6. Bundle refs consistency (spec 74-101: expanded to all 6 artifacts)
            expected_refs = {
                "review_manifest_path": "review_manifest.json",
                "review_rows_json_path": "review_rows.json",
                "review_rows_csv_path": "review_rows.csv",
                "review_summary_json_path": "review_summary.json",
                "review_summary_md_path": "review_summary.md",
                "review_handoff_contract_path": "review_handoff_contract.json",
            }
            for attr, expected_val in expected_refs.items():
                actual_val = getattr(b_refs, attr)
                if actual_val != expected_val:
                    issues.append(f"Bundle ref mismatch: {attr} is {actual_val}")
                
            # Final Context
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
        error_msg = f"Fatal bundle load error ({type(e).__name__}): {e}"
        # If we already have some issues, add this too
        issues.append(error_msg)
        return _build_error_ctx(issues)

def _build_error_ctx(issues: List[str]) -> ComparatorReviewImportContext:
    """Helper to return an error context with recorded issues."""
    return ComparatorReviewImportContext(
        manifest=None,
        handoff_contract=None,
        review_rows=(),
        summary=None,
        summary_md="",
        paths=None,
        issues=tuple(issues)
    )
