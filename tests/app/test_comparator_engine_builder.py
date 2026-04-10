import pytest
import pandas as pd
import io
import zipfile
import os
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparison_portfolio_export_builder import build_comparison_portfolio_export_bundle
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics
from iwa_rnaseq_reporter.app.comparator_matching import ComparatorMatchingContext, ComparatorMatchedReferenceSpec
from iwa_rnaseq_reporter.app.reference_dataset_registry import ReferenceDatasetSpec, ReferenceComparisonSpec, ReferenceDatasetRegistry
from iwa_rnaseq_reporter.app.comparator_engine_builder import build_comparator_result_context, compute_minimal_comparison_score

def test_compute_minimal_comparison_score_logic():
    # Setup overlapping data
    # Feature 1: Concordant
    # Feature 2: Discordant
    # Feature 3: Not in Experimental
    exp_df = pd.DataFrame({
        "feature_id": ["F1", "F2", "F4"],
        "log2_fc": [2.0, -1.5, 0.5],
        "padj": [0.01, 0.02, 0.5]
    })
    ref_df = pd.DataFrame({
        "feature_id": ["F1", "F2", "F3"],
        "log2_fc": [1.5, 1.2, 0.8], # Now F1, F2 are Top 2 in both
        "padj": [0.001, 0.01, 0.001]
    })
    
    score = compute_minimal_comparison_score(exp_df, ref_df, top_n=2)
    
    assert score.n_overlap_features == 2 # F1, F2
    assert score.n_top_n_overlap_features == 2 # F1, F2 are Top 2 in both
    # Sig overlap: F1 (up/up), F2 (down/up) -> Concordance = 0.5
    # Since signs for F1 match, but F2 is -1.5 vs 1.2
    assert score.direction_concordance == 0.5

def test_full_engine_flow_with_zip(tmp_path):
    """
    Integration test:
    1. Manually create experimental ZIP with deg_results.csv.
    2. Create reference CSV on disk.
    3. Run engine.
    """
    # 1. Experimental Setup (Manual ZIP creation)
    shared_features = ["G1", "G2", "G3"]
    exp_results = pd.DataFrame({
        "feature_id": shared_features,
        "log2_fc": [3.0, 2.0, 1.0],
        "padj": [0.001, 0.01, 0.04]
    })
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("comparisons/comp-1/deg_results.csv", exp_results.to_csv(index=False))
        # Add a dummy handoff contract just in case, though the builder/engine-builder we're testing
        # currently reads from the registry to resolve reference details.
        zf.writestr("comparisons/comp-1/handoff_contract.json", "{}")
    
    bundle_bytes = buf.getvalue()
    
    # 2. Reference Setup
    ref_csv_path = tmp_path / "ref_results.csv"
    ref_results = pd.DataFrame({
        "feature_id": shared_features,
        "log2_fc": [2.5, 1.8, 0.9], # Highly concordant
        "padj": [0.0001, 0.001, 0.01]
    })
    ref_results.to_csv(ref_csv_path, index=False)
    
    ref_rc = ReferenceComparisonSpec("ref-c1", "Ref Comp 1", "A", "B", str(ref_csv_path))
    ref_ds = ReferenceDatasetSpec("ds-1", "DS 1", "S1", "human", "gene_tpm", "ENSEMBL", (ref_rc,))
    registry = ReferenceDatasetRegistry((ref_ds,))
    
    # 3. Matching Context Mock
    mock_matching = MagicMock(spec=ComparatorMatchingContext)
    mock_matching.matched_references = (
        ComparatorMatchedReferenceSpec("comp-1", "ds-1", "ref-c1", "gene_tpm", "ENSEMBL"),
    )
    mock_summary = MagicMock()
    mock_summary.is_ready_for_reference_matching = True
    mock_matching.summary = mock_summary
    
    # 4. RUN ENGINE
    ctx = build_comparator_result_context(mock_matching, bundle_bytes, registry)
    
    assert ctx.summary.n_successful_matches == 1
    assert ctx.match_results[0].score.n_overlap_features == 3
    assert ctx.match_results[0].score.direction_concordance == 1.0 # All signs match
    assert ctx.match_results[0].score.signed_effect_correlation > 0.9
    assert ctx.summary.is_ready_for_export is True

def test_engine_skips_on_bad_data(tmp_path):
    # Reference CSV with missing columns
    bad_csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"wrong_col": [1, 2, 3]}).to_csv(bad_csv_path, index=False)
    
    bundle_bytes = b"fake_zip" # Won't even get to read zip if ref fails first or vice-versa
    
    # Simplified setup to trigger skip
    mock_matching = MagicMock()
    mock_matching.matched_references = (
        ComparatorMatchedReferenceSpec("c1", "ds1", "rc1", "gene_tpm", "ENSEMBL"),
    )
    
    ref_rc = ReferenceComparisonSpec("rc1", "L", "A", "B", str(bad_csv_path))
    ref_ds = ReferenceDatasetSpec("ds1", "D", "S", "species", "gene_tpm", "ENSEMBL", (ref_rc,))
    registry = ReferenceDatasetRegistry((ref_ds,))
    
    # We need a real-looking ZIP for the loader to not fail fatally on zip structure
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("comparisons/c1/deg_results.csv", "feature_id,log2_fc,padj\nF1,1.0,0.01")
    
    ctx = build_comparator_result_context(mock_matching, buf.getvalue(), registry)
    
    assert ctx.summary.n_successful_matches == 0
    assert ctx.summary.n_skipped_matches == 1
    assert "reference_missing_required_columns" in ctx.skipped_matches[0].reason_codes
    assert ctx.summary.is_ready_for_export is False
