from typing import List, Tuple
from .comparator_intake import ComparatorIntakeContext, ComparatorAcceptedComparisonRefSpec
from .reference_dataset_registry import ReferenceDatasetRegistry, ReferenceDatasetSpec
from .comparator_matching import (
    ComparatorMatchedReferenceSpec,
    ComparatorUnmatchedComparisonSpec,
    ComparatorMatchingIssueSpec,
    ComparatorMatchingSummarySpec,
    ComparatorMatchingContext
)

def is_reference_dataset_compatible(
    comparison: ComparatorAcceptedComparisonRefSpec,
    dataset: ReferenceDatasetSpec
) -> Tuple[bool, List[str]]:
    """
    Check if an accepted comparison is compatible with a reference dataset.
    Returns (is_compatible, list_of_warning_codes).
    """
    warnings = []
    
    # Mandatory structural checks
    if comparison.matrix_kind != dataset.matrix_kind:
        return False, []
    if comparison.feature_id_system != dataset.feature_id_system:
        return False, []
        
    # Species check (Relaxed if comparison species is unknown as per spec 7-3)
    if comparison.species is None:
        warnings.append("species_unavailable")
    else:
        if comparison.species != dataset.species:
            return False, []
            
    return True, warnings

def build_comparator_matching_context(
    intake_context: ComparatorIntakeContext,
    registry: ReferenceDatasetRegistry
) -> ComparatorMatchingContext:
    """
    Orchestrate the matching process: Accepted Comparisons vs Reference Registry.
    """
    matched_refs: List[ComparatorMatchedReferenceSpec] = []
    unmatched: List[ComparatorUnmatchedComparisonSpec] = []
    issues: List[ComparatorMatchingIssueSpec] = []

    # 1. Matching Logic
    for ac in intake_context.accepted_comparisons:
        cid = ac.comparison_id
        current_matches = 0
        
        for ds in registry.datasets:
            compatible, warnings = is_reference_dataset_compatible(ac, ds)
            
            if compatible:
                # Track warnings as issues
                for w in warnings:
                    issues.append(ComparatorMatchingIssueSpec(
                        issue_code=w,
                        severity="warning",
                        message=f"Matching {cid} with {ds.reference_dataset_id}: Species check bypassed.",
                        comparison_id=cid,
                        reference_dataset_id=ds.reference_dataset_id
                    ))
                
                # Add all available comparisons in this dataset as candidates
                for rc in ds.available_comparisons:
                    matched_refs.append(ComparatorMatchedReferenceSpec(
                        comparison_id=cid,
                        reference_dataset_id=ds.reference_dataset_id,
                        reference_comparison_id=rc.reference_comparison_id,
                        matrix_kind=ds.matrix_kind,
                        feature_id_system=ds.feature_id_system
                    ))
                    current_matches += 1
        
        if current_matches == 0:
            unmatched.append(ComparatorUnmatchedComparisonSpec(
                comparison_id=cid,
                comparison_label=ac.comparison_label,
                reason_codes=("no_compatible_reference_dataset",)
            ))

    # 2. Portfolio-level issues
    if not registry.datasets:
        issues.append(ComparatorMatchingIssueSpec(
            issue_code="empty_registry",
            severity="warning",
            message="Reference dataset registry is empty."
        ))

    # 3. Summary and Readiness (8-1)
    matched_cid_count = len(set(m.comparison_id for m in matched_refs))
    
    # Readiness logic: Need intake ready AND at least 1 match
    is_ready = (
        intake_context.summary.is_ready_for_reference_matching and
        len(matched_refs) > 0
    )

    summary = ComparatorMatchingSummarySpec(
        n_accepted_comparisons=len(intake_context.accepted_comparisons),
        n_matched_comparisons=matched_cid_count,
        n_unmatched_comparisons=len(unmatched),
        n_total_matches=len(matched_refs),
        is_ready_for_comparison_engine=is_ready
    )

    return ComparatorMatchingContext(
        intake_context=intake_context,
        registry=registry,
        matched_references=tuple(matched_refs),
        unmatched_comparisons=tuple(unmatched),
        issues=tuple(issues),
        summary=summary
    )
