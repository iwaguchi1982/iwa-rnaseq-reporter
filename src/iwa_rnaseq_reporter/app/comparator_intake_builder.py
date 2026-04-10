from typing import List, Set, Tuple
from .comparator_intake import (
    ComparatorIntakeContext,
    ComparatorAcceptedComparisonRefSpec,
    ComparatorRejectedComparisonRefSpec,
    ComparatorValidationIssueSpec,
    ComparatorIntakeSummarySpec
)
from .comparator_bundle_reader import ComparatorBundleReader
from .comparison_portfolio_handoff import ComparisonPortfolioHandoffPayload
from .deg_handoff_contract import DegHandoffPayload

def build_comparator_intake_context_from_bundle(bundle_bytes: bytes) -> ComparatorIntakeContext:
    """
    Load a portfolio bundle, validate its contents, and build an intake context.
    """
    reader = ComparatorBundleReader(bundle_bytes)
    
    # 1. Loading Root Files (Fatal validation 8-1)
    try:
        if not reader.file_exists("portfolio_manifest.json"):
            raise ValueError("portfolio_manifest.json is missing.")
        if not reader.file_exists("comparison_index.json"):
            raise ValueError("comparison_index.json is missing.")
        if not reader.file_exists("portfolio_handoff_contract.json"):
            raise ValueError("portfolio_handoff_contract.json is missing.")
        
        root_handoff = reader.load_portfolio_handoff()
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to load root portfolio contract: {e}")

    # 2. Comparison-level validation and classification
    accepted_refs: List[ComparatorAcceptedComparisonRefSpec] = []
    rejected_refs: List[ComparatorRejectedComparisonRefSpec] = []
    issues: List[ComparatorValidationIssueSpec] = []

    if not root_handoff.included_comparison_ids:
        raise ValueError("portfolio_handoff_contract.json has no comparison IDs.")

    for contract_ref in root_handoff.included_comparisons:
        cid = contract_ref.comparison_id
        path = contract_ref.handoff_contract_path
        rejection_codes = []

        # Validate path (8-1)
        if not reader.file_exists(path):
            rejection_codes.append("FILE_NOT_FOUND")
            rejected_refs.append(ComparatorRejectedComparisonRefSpec(
                comparison_id=cid,
                comparison_label=contract_ref.comparison_label,
                matrix_kind=contract_ref.matrix_kind,
                feature_id_system=None,
                handoff_contract_path=path,
                rejection_codes=tuple(rejection_codes)
            ))
            issues.append(ComparatorValidationIssueSpec("MISSING_LEAF", "fatal", f"Comparison {cid} leaf handoff missing.", cid))
            continue

        try:
            leaf_handoff = reader.load_deg_handoff(path)
            
            # Comparison-level validation (8-2, 9-1)
            # ID mismatch
            if leaf_handoff.identity.comparison_id != cid:
                rejection_codes.append("ID_MISMATCH")
            
            label = leaf_handoff.identity.comparison_label
            if not label:
                rejection_codes.append("EMPTY_LABEL")

            mk = leaf_handoff.analysis_metadata.get("matrix_kind")
            if not mk:
                rejection_codes.append("EMPTY_MATRIX_KIND")

            idsys = leaf_handoff.feature_id_system
            if idsys in [None, "", "unknown"]:
                rejection_codes.append("UNKNOWN_ID_SYSTEM")

            if rejection_codes:
                rejected_refs.append(ComparatorRejectedComparisonRefSpec(
                    comparison_id=cid,
                    comparison_label=label or contract_ref.comparison_label,
                    matrix_kind=mk or contract_ref.matrix_kind,
                    feature_id_system=idsys,
                    handoff_contract_path=path,
                    rejection_codes=tuple(rejection_codes)
                ))
                issues.append(ComparatorValidationIssueSpec("REJECTED", "warning", f"Comparison {cid} rejected: {', '.join(rejection_codes)}", cid))
            else:
                accepted_refs.append(ComparatorAcceptedComparisonRefSpec(
                    comparison_id=cid,
                    comparison_label=label,
                    matrix_kind=mk,
                    feature_id_system=idsys,
                    handoff_contract_path=path
                ))

        except Exception as e:
            rejected_refs.append(ComparatorRejectedComparisonRefSpec(
                comparison_id=cid,
                comparison_label=contract_ref.comparison_label,
                matrix_kind=contract_ref.matrix_kind,
                feature_id_system=None,
                handoff_contract_path=path,
                rejection_codes=("LOAD_ERROR",)
            ))
            issues.append(ComparatorValidationIssueSpec("LOAD_ERROR", "fatal", f"Comparison {cid} load failed: {e}", cid))

    # 3. Summary and Readiness (5-3, 9-3)
    matrix_kinds = tuple(sorted(list(set(r.matrix_kind for r in accepted_refs))))
    id_systems = tuple(sorted(list(set(r.feature_id_system for r in accepted_refs))))
    
    has_mixed_matrix = len(matrix_kinds) > 1
    has_mixed_id = len(id_systems) > 1
    
    if has_mixed_matrix:
        issues.append(ComparatorValidationIssueSpec("MIXED_MATRIX", "warning", "Portfolio has mixed matrix kinds."))
    if has_mixed_id:
        issues.append(ComparatorValidationIssueSpec("MIXED_ID_SYSTEM", "warning", "Portfolio has mixed feature ID systems."))
    if not accepted_refs:
        issues.append(ComparatorValidationIssueSpec("NO_ACCEPTED_COMPARISONS", "warning", "No comparisons were accepted for analysis."))

    # Readiness logic (5-3)
    is_ready = (
        len(accepted_refs) > 0 and 
        not has_mixed_matrix and 
        not has_mixed_id and 
        all(r.feature_id_system not in [None, "", "unknown"] for r in accepted_refs)
    )

    summary = ComparatorIntakeSummarySpec(
        portfolio_id=root_handoff.portfolio_id,
        n_total_comparisons=len(root_handoff.included_comparison_ids),
        n_accepted_comparisons=len(accepted_refs),
        n_rejected_comparisons=len(rejected_refs),
        matrix_kinds=matrix_kinds,
        feature_id_systems=id_systems,
        has_mixed_matrix_kinds=has_mixed_matrix,
        has_mixed_feature_id_systems=has_mixed_id,
        is_ready_for_reference_matching=is_ready
    )

    return ComparatorIntakeContext(
        portfolio_handoff=root_handoff,
        accepted_comparisons=tuple(accepted_refs),
        rejected_comparisons=tuple(rejected_refs),
        issues=tuple(issues),
        summary=summary
    )
