import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from .comparator_matching import ComparatorMatchingContext, ComparatorMatchedReferenceSpec
from .comparator_engine import (
    ComparatorScoreSpec,
    ComparatorMatchResultSpec,
    ComparatorSkippedMatchSpec,
    ComparatorEngineIssueSpec,
    ComparatorResultSummarySpec,
    ComparatorResultContext
)
from .comparator_result_table_loader import ComparatorResultTableLoader, validate_result_table_columns
from .reference_dataset_registry import ReferenceDatasetRegistry

def compute_minimal_comparison_score(
    exp_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    padj_threshold: float = 0.05,
    top_n: int = 100
) -> ComparatorScoreSpec:
    """
    Perform feature-level statistical comparisons between two result tables.
    """
    # 1. Feature Overlap (Inner Join)
    overlap = pd.merge(
        exp_df[["feature_id", "log2_fc", "padj"]],
        ref_df[["feature_id", "log2_fc", "padj"]],
        on="feature_id",
        suffixes=("_exp", "_ref")
    )
    
    n_overlap = len(overlap)
    
    # 2. Top-N Overlap
    # Sort both by absolute log2FC and pick top N
    exp_top = exp_df.reindex(exp_df["log2_fc"].abs().sort_values(ascending=False).index).head(top_n)
    ref_top = ref_df.reindex(ref_df["log2_fc"].abs().sort_values(ascending=False).index).head(top_n)
    
    n_top_overlap = len(set(exp_top["feature_id"]) & set(ref_top["feature_id"]))
    
    # 3. Direction Concordance (on overlapping significant features)
    sig_overlap = overlap[
        (overlap["padj_exp"] < padj_threshold) & 
        (overlap["padj_ref"] < padj_threshold)
    ]
    
    concordance = None
    if not sig_overlap.empty:
        # Check if signs of log2_fc match
        same_direction = (np.sign(sig_overlap["log2_fc_exp"]) == np.sign(sig_overlap["log2_fc_ref"])).sum()
        concordance = same_direction / len(sig_overlap)
        
    # 4. Signed Effect Correlation (Pearson)
    correlation = None
    if n_overlap >= 2:
        correlation = overlap["log2_fc_exp"].corr(overlap["log2_fc_ref"])
        if np.isnan(correlation):
            correlation = None
            
    return ComparatorScoreSpec(
        n_overlap_features=n_overlap,
        n_top_n_overlap_features=n_top_overlap,
        direction_concordance=concordance,
        signed_effect_correlation=correlation
    )

def build_comparator_result_context(
    matching_context: ComparatorMatchingContext,
    bundle_bytes: bytes,
    registry: ReferenceDatasetRegistry
) -> ComparatorResultContext:
    """
    Execute the comparison engine for all matched reference pairs.
    """
    loader = ComparatorResultTableLoader(bundle_bytes)
    
    results: List[ComparatorMatchResultSpec] = []
    skipped: List[ComparatorSkippedMatchSpec] = []
    issues: List[ComparatorEngineIssueSpec] = []
    
    # Cache for loaded reference tables to avoid re-reading same file
    ref_table_cache = {}

    for match in matching_context.matched_references:
        cid = match.comparison_id
        ds_id = match.reference_dataset_id
        rc_id = match.reference_comparison_id
        
        try:
            # Load Experimental Table
            exp_df = loader.load_experimental_result_table(cid)
            if not validate_result_table_columns(exp_df):
                skipped.append(ComparatorSkippedMatchSpec(cid, ds_id, rc_id, ("missing_required_result_columns",)))
                issues.append(ComparatorEngineIssueSpec("BAD_COLUMNS", "warning", f"Experimental table {cid} missing required columns.", cid))
                continue
                
            # Resolve Reference Spec
            # Find the dataset and then the comparison
            target_ds = next((d for d in registry.datasets if d.reference_dataset_id == ds_id), None)
            if not target_ds:
                skipped.append(ComparatorSkippedMatchSpec(cid, ds_id, rc_id, ("reference_dataset_not_found",)))
                continue
            
            target_rc = next((c for c in target_ds.available_comparisons if c.reference_comparison_id == rc_id), None)
            if not target_rc:
                skipped.append(ComparatorSkippedMatchSpec(cid, ds_id, rc_id, ("reference_comparison_not_found",)))
                continue

            # Load Reference Table (with caching)
            ref_cache_key = target_rc.result_ref
            if ref_cache_key not in ref_table_cache:
                ref_table_cache[ref_cache_key] = loader.load_reference_result_table(target_rc)
            
            ref_df = ref_table_cache[ref_cache_key]
            
            if not validate_result_table_columns(ref_df):
                skipped.append(ComparatorSkippedMatchSpec(cid, ds_id, rc_id, ("reference_missing_required_columns",)))
                issues.append(ComparatorEngineIssueSpec("BAD_REF_COLUMNS", "warning", f"Reference table {rc_id} missing required columns.", cid, ds_id, rc_id))
                continue
            
            # Compute Score
            score = compute_minimal_comparison_score(exp_df, ref_df)
            
            results.append(ComparatorMatchResultSpec(
                comparison_id=cid,
                reference_dataset_id=ds_id,
                reference_comparison_id=rc_id,
                experimental_result_path=f"comparisons/{cid}/deg_results.csv",
                reference_result_ref=target_rc.result_ref,
                score=score
            ))

        except Exception as e:
            skipped.append(ComparatorSkippedMatchSpec(cid, ds_id, rc_id, ("calculation_error",)))
            issues.append(ComparatorEngineIssueSpec("CALC_ERROR", "warning", f"Calculated failed for {cid} vs {rc_id}: {e}", cid, ds_id, rc_id))

    # Summary (184)
    successful_count = len(results)
    comparison_ids_with_results = len(set(r.comparison_id for r in results))
    
    summary = ComparatorResultSummarySpec(
        n_total_matches_requested=len(matching_context.matched_references),
        n_successful_matches=successful_count,
        n_skipped_matches=len(skipped),
        n_comparisons_with_results=comparison_ids_with_results,
        is_ready_for_export=(successful_count > 0)
    )

    return ComparatorResultContext(
        matching_context=matching_context,
        match_results=tuple(results),
        skipped_matches=tuple(skipped),
        issues=tuple(issues),
        summary=summary
    )
