import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
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
    Resolve absolute paths for all bundle components based on a manifest or root dir.
    """
    p = Path(manifest_path_like).resolve()
    
    if p.is_dir():
        bundle_root = p
        manifest_path = p / STABLE_MANIFEST_NAME
    else:
        bundle_root = p.parent
        manifest_path = p

    if not manifest_path.exists():
        raise FileNotFoundError(f"Consensus manifest not found at {manifest_path}")

    # Load manifest to find other artifacts (minimal load)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Resolve Handoff
    handoff_path = bundle_root / STABLE_HANDOFF_NAME
    
    # Resolve other known artifacts from v0.18.4 baseline
    summary_path = bundle_root / "report_summary.md"
    results_path = bundle_root / "consensus_decisions.csv"

    return ConsensusBundlePaths(
        manifest_path=manifest_path,
        bundle_root=bundle_root,
        handoff_contract_path=handoff_path if handoff_path.exists() else None,
        summary_path=summary_path if summary_path.exists() else None,
        results_table_path=results_path if results_path.exists() else None
    )

def evaluate_consensus_bundle_contract(
    manifest: Dict[str, Any],
    handoff: Optional[Dict[str, Any]] = None
) -> ConsensusBundleContractInfo:
    """
    Assess schema compatibility and identity.
    """
    m_schema = manifest.get("schema_name", "unknown")
    m_version = manifest.get("schema_version", "unknown")
    h_schema = handoff.get("schema_name") if handoff else None
    h_version = handoff.get("schema_version") if handoff else None
    
    is_supported = (m_schema == EXPECTED_MANIFEST_SCHEMA)
    status = "supported" if is_supported else "unsupported_schema"
    
    if is_supported and m_version != "0.19.1":
        status = "version_mismatch" # Future proofing
        
    return ConsensusBundleContractInfo(
        schema_name=m_schema,
        schema_version=m_version,
        handoff_schema_name=h_schema,
        handoff_schema_version=h_version,
        is_supported=is_supported,
        compatibility_status=status
    )

def read_consensus_bundle(
    manifest_path_like: Any,
    load_tables: bool = True
) -> ConsensusBundleImportContext:
    """
    High-level reader for valid consensus bundles. Raises exceptions on failure.
    """
    paths = resolve_consensus_bundle_paths(manifest_path_like)
    
    with open(paths.manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    handoff = None
    if paths.handoff_contract_path:
        with open(paths.handoff_contract_path, "r", encoding="utf-8") as f:
            handoff = json.load(f)
            
    contract_info = evaluate_consensus_bundle_contract(manifest, handoff)
    if not contract_info.is_supported:
        raise ValueError(f"Unsupported consensus bundle schema: {contract_info.schema_name}")

    return ConsensusBundleImportContext(
        manifest=manifest,
        handoff_contract=handoff,
        paths=paths,
        contract_info=contract_info
    )

def validate_consensus_bundle(manifest_path_like: Any) -> ConsensusBundleValidationResult:
    """
    Diagnostic validator that collects issues instead of raising exceptions.
    """
    issues: List[ConsensusBundleValidationIssueSpec] = []
    
    # 1. Path Resolution
    try:
        paths = resolve_consensus_bundle_paths(manifest_path_like)
        bundle_root = paths.bundle_root
        manifest_path = paths.manifest_path
    except Exception as e:
        return ConsensusBundleValidationResult(
            manifest_path=Path(manifest_path_like),
            bundle_root=Path(manifest_path_like).parent,
            contract_info=ConsensusBundleContractInfo("unknown", "unknown", None, None, False, "path_error"),
            is_valid=False,
            error_count=1,
            warning_count=0,
            issues=(ConsensusBundleValidationIssueSpec("error", "resolution_failed", str(e)),)
        )

    # 2. Manifest JSON
    manifest = {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        issues.append(ConsensusBundleValidationIssueSpec("error", "invalid_manifest_json", str(e), path=str(manifest_path)))

    # 3. Contract Evaluation
    handoff = {}
    if paths.handoff_contract_path:
        try:
            with open(paths.handoff_contract_path, "r", encoding="utf-8") as f:
                handoff = json.load(f)
        except:
            pass
            
    contract_info = evaluate_consensus_bundle_contract(manifest, handoff if handoff else None)
    if not contract_info.is_supported:
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "unsupported_schema", 
            f"Expected {EXPECTED_MANIFEST_SCHEMA}, found {contract_info.schema_name}",
            field_name="schema_name"
        ))

    # 4. Required Fields Check (v0.19.1)
    for field in ["schema_name", "schema_version", "generated_at", "provenance"]:
        if field not in manifest:
            issues.append(ConsensusBundleValidationIssueSpec("error", "missing_required_field", f"Field '{field}' is missing in manifest", field_name=field))

    # 5. Provenance Deep Check
    prov = manifest.get("provenance", {})
    if not isinstance(prov, dict):
        issues.append(ConsensusBundleValidationIssueSpec("error", "invalid_provenance_type", "Provenance must be a dictionary", field_name="provenance"))
    else:
        for pfield in ["producer_app", "producer_version", "source_consensus_run_id"]:
            if pfield not in prov:
                issues.append(ConsensusBundleValidationIssueSpec("error", "missing_provenance_field", f"Provenance field '{pfield}' is missing", field_name=f"provenance.{pfield}"))

    # 6. Artifact Existence
    if not paths.handoff_contract_path:
        issues.append(ConsensusBundleValidationIssueSpec("error", "missing_handoff_contract", "Handoff contract file is missing", artifact_name="handoff"))
    
    if not paths.summary_path:
        issues.append(ConsensusBundleValidationIssueSpec("warning", "missing_summary_md", "Report summary markdown is missing", artifact_name="summary"))

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    return ConsensusBundleValidationResult(
        manifest_path=manifest_path,
        bundle_root=bundle_root,
        contract_info=contract_info,
        is_valid=len(errors) == 0,
        error_count=len(errors),
        warning_count=len(warnings),
        issues=tuple(issues)
    )
