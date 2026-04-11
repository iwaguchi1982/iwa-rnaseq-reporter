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
    elif m_version not in ["0.19.1", "0.19.3"]:
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

def _validate_execution_config(
    cfg: Any,
    obj_label: str,
    issues: List[ConsensusBundleValidationIssueSpec]
):
    """
    Check the structure of the execution config container.
    """
    if not isinstance(cfg, dict):
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "invalid_execution_config_type", 
            f"Execution config in {obj_label} must be a dictionary", 
            field_name=f"{obj_label}.execution_config"
        ))
        return

    # 1. Top-level fields
    core_fields = ["config_name", "config_version", "config_source", "ranking", "consensus"]
    for f in core_fields:
        if f not in cfg:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "missing_config_field", 
                f"Config field '{f}' is missing in {obj_label}.execution_config", 
                field_name=f"{obj_label}.execution_config.{f}"
            ))

    # 2. Ranking block
    if "ranking" in cfg and isinstance(cfg["ranking"], dict):
        r = cfg["ranking"]
        r_fields = [
            "overlap_weight", "top_n_overlap_weight", "concordance_weight", 
            "correlation_weight", "tie_tolerance", "exact_tie_epsilon"
        ]
        for f in r_fields:
            if f not in r:
                issues.append(ConsensusBundleValidationIssueSpec(
                    "error", "missing_ranking_field", 
                    f"Ranking parameter '{f}' is missing", 
                    field_name=f"{obj_label}.execution_config.ranking.{f}"
                ))
    
    # 3. Consensus block
    if "consensus" in cfg and isinstance(cfg["consensus"], dict):
        c = cfg["consensus"]
        c_fields = [
            "candidate_sort_policy", "consensus_margin_threshold", "minimum_supporting_references", 
            "weak_support_mean_threshold", "top_rank_conflict_policy", "weak_margin_policy", 
            "insufficient_support_policy"
        ]
        for f in c_fields:
            if f not in c:
                issues.append(ConsensusBundleValidationIssueSpec(
                    "error", "missing_consensus_field", 
                    f"Consensus parameter '{f}' is missing", 
                    field_name=f"{obj_label}.execution_config.consensus.{f}"
                ))

def _validate_decision_support_block(ds: Any, obj_label: str, issues: List[ConsensusBundleValidationIssueSpec]):
    """
    Check the structural integrity of the decision support block.
    Corresponds to spec 5.1.
    """
    if not isinstance(ds, dict):
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "invalid_decision_support_type", 
            f"Decision support in {obj_label} must be a dictionary", 
            field_name=f"{obj_label}.decision_support"
        ))
        return

    # 1. Top-level required
    core_fields = ["schema_name", "schema_version", "decision_evidence_refs", "summary"]
    for f in core_fields:
        if f not in ds:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "missing_decision_support_field", 
                f"Field '{f}' is missing in {obj_label}.decision_support", 
                field_name=f"{obj_label}.decision_support.{f}"
            ))

    # 2. Schema check
    if ds.get("schema_name") != "ComparatorDecisionSupportPayload":
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "invalid_decision_support_schema", 
            f"Expected schema 'ComparatorDecisionSupportPayload', got '{ds.get('schema_name')}'",
            field_name=f"{obj_label}.decision_support.schema_name"
        ))
    if ds.get("schema_version") != "0.19.4.1":
        issues.append(ConsensusBundleValidationIssueSpec(
            "warning", "decision_support_version_mismatch",
            f"Expected version '0.19.4.1', got '{ds.get('schema_version')}'",
            field_name=f"{obj_label}.decision_support.schema_version"
        ))

    # 3. Summary check
    summary = ds.get("summary")
    if isinstance(summary, dict):
        sum_fields = ["n_decision_refs", "n_consensus", "n_abstain", "n_no_consensus", "n_insufficient_evidence"]
        for f in sum_fields:
            if f not in summary:
                issues.append(ConsensusBundleValidationIssueSpec(
                    "error", "missing_decision_support_summary_field", 
                    f"Summary field '{f}' is missing", 
                    field_name=f"{obj_label}.decision_support.summary.{f}"
                ))

    # 4. Refs check
    refs = ds.get("decision_evidence_refs")
    if isinstance(refs, (list, tuple)):
        for i, ref in enumerate(refs):
            ref_label = f"{obj_label}.decision_support.decision_evidence_refs[{i}]"
            required_ref_fields = ["comparison_id", "decision_status", "reason_codes", "evidence_stats", "artifact_refs"]
            for f in required_ref_fields:
                if f not in ref:
                    issues.append(ConsensusBundleValidationIssueSpec(
                        "error", "missing_decision_evidence_ref_field", 
                        f"Field '{f}' is missing in ref", 
                        field_name=f"{ref_label}.{f}"
                    ))
            
            # Nested stats
            stats = ref.get("evidence_stats")
            if isinstance(stats, dict):
                stat_fields = ["support_margin", "has_conflict", "has_weak_support", "n_supporting_references", "n_conflicting_references", "n_competing_candidates"]
                for f in stat_fields:
                    if f not in stats:
                        issues.append(ConsensusBundleValidationIssueSpec(
                            "error", "missing_evidence_stats_field", f"Stat '{f}' is missing",
                            field_name=f"{ref_label}.evidence_stats.{f}"
                        ))
            
            # Nested artifacts
            art_refs = ref.get("artifact_refs")
            if isinstance(art_refs, dict):
                art_fields = [
                    "consensus_manifest_path", "consensus_handoff_contract_path", "consensus_decisions_json_path",
                    "evidence_profiles_json_path", "consensus_decisions_csv_path", "report_summary_md_path"
                ]
                for f in art_fields:
                    if f not in art_refs:
                        issues.append(ConsensusBundleValidationIssueSpec(
                            "error", "missing_decision_artifact_ref", f"Artifact ref '{f}' is missing",
                            field_name=f"{ref_label}.artifact_refs.{f}"
                        ))

def _validate_decision_support_consistency(handoff: Dict[str, Any], issues: List[ConsensusBundleValidationIssueSpec]):
    """
    Check consistency between handoff body and decision support block.
    Corresponds to spec 5.2.
    """
    ds = handoff.get("decision_support")
    if not isinstance(ds, dict):
        return
        
    ds_refs = ds.get("decision_evidence_refs", [])
    handoff_refs = handoff.get("comparison_decision_refs", [])
    included_ids = handoff.get("included_comparison_ids", [])
    
    # 1. Case Count
    if len(ds_refs) != len(included_ids):
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "decision_support_count_mismatch",
            f"Decision support refs count ({len(ds_refs)}) does not match included comparisons ({len(included_ids)})",
            field_name="handoff.decision_support.decision_evidence_refs"
        ))

    # 2. Summary count
    ds_summary = ds.get("summary", {})
    if ds_summary.get("n_decision_refs") != len(ds_refs):
        issues.append(ConsensusBundleValidationIssueSpec(
            "error", "decision_support_summary_count_mismatch",
            f"Summary n_decision_refs ({ds_summary.get('n_decision_refs')}) does not match actual refs count ({len(ds_refs)})",
            field_name="handoff.decision_support.summary.n_decision_refs"
        ))

    # 3. ID and Status consistency
    ds_map = {r.get("comparison_id"): r for r in ds_refs if r.get("comparison_id")}
    h_map = {r.get("comparison_id"): r for r in handoff_refs if r.get("comparison_id")}
    
    for comp_id in included_ids:
        if comp_id not in ds_map:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "decision_support_comparison_id_mismatch",
                f"Comparison ID '{comp_id}' missing in decision_support",
                field_name="handoff.decision_support.decision_evidence_refs"
            ))
            continue
        
        # Status parity
        ds_status = ds_map[comp_id].get("decision_status")
        h_status = h_map.get(comp_id, {}).get("decision_status")
        if ds_status and h_status and ds_status != h_status:
            issues.append(ConsensusBundleValidationIssueSpec(
                "error", "decision_support_status_mismatch",
                f"Status mismatch for '{comp_id}': decision_support='{ds_status}', handoff='{h_status}'",
                field_name=f"handoff.decision_support.decision_evidence_refs[ID={comp_id}].decision_status"
            ))

    # 4. Artifact Path alignment (sample check)
    bundle_refs = handoff.get("bundle_refs", {})
    if ds_refs and isinstance(ds_refs[0], dict):
        art_refs = ds_refs[0].get("artifact_refs", {})
        # Manifest
        if art_refs.get("consensus_manifest_path") != bundle_refs.get("consensus_manifest_path"):
             issues.append(ConsensusBundleValidationIssueSpec(
                "error", "decision_support_artifact_ref_mismatch",
                f"Manifest path mismatch in support block",
                field_name="handoff.decision_support.decision_evidence_refs[0].artifact_refs.consensus_manifest_path"
            ))
        # Handoff Contract
        if art_refs.get("consensus_handoff_contract_path") != bundle_refs.get("consensus_handoff_contract_path"):
             issues.append(ConsensusBundleValidationIssueSpec(
                "error", "decision_support_artifact_ref_mismatch",
                f"Handoff contract path mismatch in support block",
                field_name="handoff.decision_support.decision_evidence_refs[0].artifact_refs.consensus_handoff_contract_path"
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
            "n_ranked_comparisons", "n_consensus", "n_abstain", "n_no_consensus", "n_insufficient_evidence",
            "execution_config"
        ], "manifest", issues)
        if "provenance" in manifest:
            _validate_provenance(manifest["provenance"], "manifest", issues)
        if "execution_config" in manifest:
            _validate_execution_config(manifest["execution_config"], "manifest", issues)
            
    if handoff:
        _validate_required_fields(handoff, [
            "schema_name", "schema_version", "generated_at", "provenance", "consensus_run_id",
            "bundle_refs", "included_comparison_ids", "comparison_decision_refs", "summary",
            "execution_config", "decision_support"
        ], "handoff", issues)
        if "provenance" in handoff:
            _validate_provenance(handoff["provenance"], "handoff", issues)
        if "execution_config" in handoff:
            _validate_execution_config(handoff["execution_config"], "handoff", issues)
        if "decision_support" in handoff:
            _validate_decision_support_block(handoff["decision_support"], "handoff", issues)
            _validate_decision_support_consistency(handoff, issues)

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
