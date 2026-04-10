import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
from .comparator_consensus_import import (
    ConsensusBundleValidationIssueSpec,
    ConsensusBundleContractInfo,
    ConsensusBundlePaths,
    ConsensusBundleImportContext,
    ConsensusBundleValidationResult
)

# Constants for stable schema identification (v0.19.1/v0.19.2)
EXPECTED_MANIFEST_SCHEMA = "ConsensusExportManifest"
EXPECTED_HANDOFF_SCHEMA = "ConsensusHandoffContract"
STABLE_MANIFEST_NAME = "consensus_manifest.json"
STABLE_HANDOFF_NAME = "consensus_handoff_contract.json"

def resolve_consensus_bundle_paths(manifest_path_like: Any) -> ConsensusBundlePaths:
    """
    STRICTLY resolve absolute paths for bundle components without parsing any files.
    """
    p = Path(manifest_path_like).resolve()
    
    if p.is_dir():
        bundle_root = p
        manifest_path = p / STABLE_MANIFEST_NAME
    else:
        bundle_root = p.parent
        manifest_path = p

    # v0.19.2a: Just define the potential paths. Existence is checked by Validator.
    handoff_path = bundle_root / STABLE_HANDOFF_NAME
    summary_path = bundle_root / "report_summary.md"
    results_path = bundle_root / "consensus_decisions.csv"
    
    # Internal JSONs if present (standard naming from v0.18.4)
    decisions_json_path = bundle_root / "consensus_decisions.json"
    evidence_profiles_path = bundle_root / "evidence_profiles.json"

    return ConsensusBundlePaths(
        manifest_path=manifest_path,
        bundle_root=bundle_root,
        handoff_contract_path=handoff_path,
        summary_path=summary_path,
        results_table_path=results_path,
        decisions_json_path=decisions_json_path,
        evidence_profiles_path=evidence_profiles_path
    )

def evaluate_consensus_bundle_contract(
    manifest: Dict[str, Any],
    handoff: Optional[Dict[str, Any]] = None,
    handoff_exists: bool = False
) -> ConsensusBundleContractInfo:
    """
    Assess schema compatibility and identity for both components.
    """
    m_schema = manifest.get("schema_name", "unknown")
    m_version = manifest.get("schema_version", "")
    
    h_schema = None
    h_version = ""
    is_supported_handoff = True

    if handoff_exists:
        if handoff is None:
            # File exists but failed to parse into a dict
            is_supported_handoff = False
            h_schema = "corrupted"
        else:
            h_schema = handoff.get("schema_name", "unknown")
            h_version = handoff.get("schema_version", "")
            is_supported_handoff = (h_schema == EXPECTED_HANDOFF_SCHEMA)
    
    is_supported_manifest = (m_schema == EXPECTED_MANIFEST_SCHEMA)
    is_supported = is_supported_manifest and is_supported_handoff
    
    status = "supported"
    if not is_supported_manifest:
        status = "unsupported_manifest_schema"
    elif handoff_exists and not is_supported_handoff:
        status = "unsupported_handoff_schema"
    elif not m_version or (handoff and not h_version):
        status = "missing_schema_version"
    elif m_version != "0.19.1":
        status = "version_mismatch"
        
    return ConsensusBundleContractInfo(
        schema_name=m_schema,
        schema_version=m_version,
        handoff_schema_name=h_schema,
        handoff_schema_version=h_version,
        is_supported=is_supported and status == "supported",
        compatibility_status=status
    )

def _validate_required_fields(
    obj: Dict[str, Any], 
    required_fields: List[str], 
    obj_label: str, 
    issues: List[ConsensusBundleValidationIssueSpec]
):
    for field in required_fields:
        if field not in obj:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "missing_required_field", 
                f"Field '{field}' is missing in {obj_label}", 
                field_name=field
            ))

def _validate_provenance(
    prov: Any, 
    obj_label: str, 
    issues: List[ConsensusBundleValidationIssueSpec]
):
    if not isinstance(prov, dict):
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "invalid_provenance_type", 
            f"Provenance in {obj_label} must be a dictionary", 
            field_name=f"{obj_label}.provenance"
        ))
        return

    core_fields = ["producer_app", "producer_version", "source_consensus_run_id"]
    for f in core_fields:
        if f not in prov or prov[f] is None:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "missing_provenance_field", 
                f"Provenance field '{f}' is missing in {obj_label}", 
                field_name=f"{obj_label}.provenance.{f}"
            ))
            
    lineage_fields = ["source_portfolio_id", "source_comparator_run_id", "source_bundle_filename", "content_digest"]
    for f in lineage_fields:
        if f not in prov:
            issues.append(ConsensusBundleValidationIssueSpec(
                "warning", "missing_lineage_field", 
                f"Optional lineage field '{f}' is missing in {obj_label}.provenance", 
                field_name=f"{obj_label}.provenance.{f}"
            ))

def validate_consensus_bundle(manifest_path_like: Any) -> ConsensusBundleValidationResult:
    """
    Exhaustively collect issues from the bundle components.
    """
    issues: List[ConsensusBundleValidationIssueSpec] = []
    paths = resolve_consensus_bundle_paths(manifest_path_like)
    
    # 1. Manifest
    manifest = {}
    if not paths.manifest_path.exists():
        issues.append(ConsensusBundleValidationIssueSpec("error", "manifest_missing", f"Manifest not found at {paths.manifest_path}"))
    else:
        try:
            with open(paths.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            issues.append(ConsensusBundleValidationIssueSpec("error", "invalid_manifest_json", str(e), path=str(paths.manifest_path)))

    # 2. Handoff
    handoff = None
    if not paths.handoff_contract_path.exists():
        issues.append(ConsensusBundleValidationIssueSpec("error", "handoff_missing", "Handoff contract is missing", artifact_name="handoff"))
    else:
        try:
            with open(paths.handoff_contract_path, "r", encoding="utf-8") as f:
                handoff = json.load(f)
        except Exception as e:
            issues.append(ConsensusBundleValidationIssueSpec("error", "invalid_handoff_json", str(e), path=str(paths.handoff_contract_path)))

    # 3. Contract Logic
    contract_info = evaluate_consensus_bundle_contract(
        manifest, 
        handoff, 
        handoff_exists=paths.handoff_contract_path.exists()
    )
    if not contract_info.is_supported:
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "unsupported_bundle_contract", 
            f"Compatibility check failed: {contract_info.compatibility_status}"
        ))

    # 4. Field Details
    if manifest:
        _validate_required_fields(manifest, [
            "schema_name", "schema_version", "generated_at", "provenance", "consensus_run_id",
            "n_ranked_comparisons", "n_consensus", "n_abstain", "n_no_consensus", "n_insufficient_evidence"
        ], "manifest", issues)
        if "provenance" in manifest:
            _validate_provenance(manifest["provenance"], "manifest", issues)
            
    if handoff:
        _validate_required_fields(handoff, [
            "schema_name", "schema_version", "generated_at", "provenance", "consensus_run_id",
            "bundle_refs", "included_comparison_ids", "comparison_decision_refs", "summary"
        ], "handoff", issues)
        if "provenance" in handoff:
            _validate_provenance(handoff["provenance"], "handoff", issues)

    # 5. Artifact existence via Bundle Refs
    if handoff and "bundle_refs" in handoff:
        refs = handoff["bundle_refs"]
        required_keys = [
            "consensus_manifest_path", "consensus_summary_path", "consensus_decisions_path", 
            "evidence_profiles_path", "consensus_handoff_contract_path"
        ]
        for k in required_keys:
            rel = refs.get(k)
            if not rel:
                issues.append(ConsensusBundleValidationIssueSpec("error", "missing_bundle_ref", f"Reference '{k}' is empty", field_name=f"bundle_refs.{k}"))
            else:
                target = paths.bundle_root / rel
                if not target.exists():
                    issues.append(ConsensusBundleValidationIssueSpec("error", "artifact_missing", f"Artifact {k} not found at {rel}", artifact_name=k))

    # Additional standard files (v0.18.4)
    if not paths.results_table_path.exists():
        issues.append(ConsensusBundleValidationIssueSpec("error", "missing_decisions_csv", "Decisions CSV is missing", artifact_name="results_table"))
    if not paths.summary_path.exists():
        issues.append(ConsensusBundleValidationIssueSpec("warning", "missing_summary_md", "Summary markdown is missing", artifact_name="summary_md"))

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    return ConsensusBundleValidationResult(
        manifest_path=paths.manifest_path,
        bundle_root=paths.bundle_root,
        contract_info=contract_info,
        is_valid=len(errors) == 0,
        error_count=len(errors),
        warning_count=len(warnings),
        issues=tuple(issues),
        resolved_artifacts=tuple(sorted(list(set(i.artifact_name for i in issues if i.artifact_name))))
    )

def read_consensus_bundle(
    manifest_path_like: Any,
    load_tables: bool = True
) -> ConsensusBundleImportContext:
    """
    High-level reader that populates the context with real data.
    """
    # Use validator internally to ensure it's worth reading
    v_res = validate_consensus_bundle(manifest_path_like)
    if not v_res.is_valid:
        msg = "; ".join(i.message for i in v_res.issues if i.level == "error")
        raise ValueError(f"Cannot read invalid consensus bundle: {msg}")

    paths = resolve_consensus_bundle_paths(manifest_path_like)
    
    with open(paths.manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    with open(paths.handoff_contract_path, "r", encoding="utf-8") as f:
        handoff = json.load(f)
            
    summary_markdown = None
    if paths.summary_path.exists():
        with open(paths.summary_path, "r", encoding="utf-8") as f:
            summary_markdown = f.read()
            
    results_table = None
    if load_tables and paths.results_table_path.exists():
        results_table = pd.read_csv(paths.results_table_path)
        
    decisions_json = None
    if paths.decisions_json_path.exists():
        with open(paths.decisions_json_path, "r", encoding="utf-8") as f:
            decisions_json = json.load(f)
            
    evidence_profiles_json = None
    if paths.evidence_profiles_path.exists():
        with open(paths.evidence_profiles_path, "r", encoding="utf-8") as f:
            evidence_profiles_json = json.load(f)

    return ConsensusBundleImportContext(
        manifest=manifest,
        handoff_contract=handoff,
        paths=paths,
        contract_info=v_res.contract_info,
        summary_markdown=summary_markdown,
        results_table=results_table,
        decisions_json=decisions_json,
        evidence_profiles_json=evidence_profiles_json
    )
