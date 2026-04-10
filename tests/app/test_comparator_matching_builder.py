import pytest
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_intake import (
    ComparatorIntakeContext,
    ComparatorAcceptedComparisonRefSpec,
    ComparatorIntakeSummarySpec
)
from iwa_rnaseq_reporter.app.reference_dataset_registry import (
    ReferenceDatasetSpec,
    ReferenceComparisonSpec,
    ReferenceDatasetRegistry
)
from iwa_rnaseq_reporter.app.comparator_matching_builder import (
    build_comparator_matching_context,
    is_reference_dataset_compatible
)

def test_is_reference_dataset_compatible_logic():
    # 1. Exact match
    comp = ComparatorAcceptedComparisonRefSpec("c1", "L1", "gene_tpm", "ENSEMBL", "p.json", "human")
    ds = ReferenceDatasetSpec("ds1", "D1", "S1", "human", "gene_tpm", "ENSEMBL")
    compatible, warnings = is_reference_dataset_compatible(comp, ds)
    assert compatible is True
    assert not warnings

    # 2. Species mismatch
    ds_mouse = ReferenceDatasetSpec("ds2", "D2", "S2", "mouse", "gene_tpm", "ENSEMBL")
    compatible, _ = is_reference_dataset_compatible(comp, ds_mouse)
    assert compatible is False

    # 3. Species unknown in comparison (Relaxed match)
    comp_no_sp = ComparatorAcceptedComparisonRefSpec("c1", "L1", "gene_tpm", "ENSEMBL", "p.json", None)
    compatible, warnings = is_reference_dataset_compatible(comp_no_sp, ds)
    assert compatible is True
    assert "species_unavailable" in warnings

    # 4. MatrixKind mismatch
    ds_counts = ReferenceDatasetSpec("ds3", "D3", "S3", "human", "counts", "ENSEMBL")
    compatible, _ = is_reference_dataset_compatible(comp, ds_counts)
    assert compatible is False

def test_build_matching_context_success():
    # Setup Intake Context
    mock_intake = MagicMock(spec=ComparatorIntakeContext)
    ac1 = ComparatorAcceptedComparisonRefSpec("c1", "Label 1", "gene_tpm", "ENSEMBL", "path/1.json", "human")
    mock_intake.accepted_comparisons = (ac1,)
    
    mock_summary = MagicMock()
    mock_summary.is_ready_for_reference_matching = True
    mock_intake.summary = mock_summary
    
    # Setup Registry
    ds1 = ReferenceDatasetSpec(
        "ds1", "TCGA_LIHC", "TCGA", "human", "gene_tpm", "ENSEMBL",
        available_comparisons=(
            ReferenceComparisonSpec("ref_comp_1", "T vs N", "T", "N", "ref.json"),
        )
    )
    registry = ReferenceDatasetRegistry(datasets=(ds1,))
    
    # Build Context
    ctx = build_comparator_matching_context(mock_intake, registry)
    
    assert ctx.summary.n_accepted_comparisons == 1
    assert ctx.summary.n_matched_comparisons == 1
    assert ctx.summary.n_total_matches == 1
    assert ctx.matched_references[0].reference_comparison_id == "ref_comp_1"
    assert ctx.summary.is_ready_for_comparison_engine is True

def test_matching_with_no_compatible_references():
    mock_intake = MagicMock(spec=ComparatorIntakeContext)
    # Comparison is SYMBOL, but Registry only has ENSEMBL
    ac1 = ComparatorAcceptedComparisonRefSpec("c1", "Label 1", "gene_tpm", "SYMBOL", "path/1.json", "human")
    mock_intake.accepted_comparisons = (ac1,)
    
    mock_summary = MagicMock()
    mock_summary.is_ready_for_reference_matching = True
    mock_intake.summary = mock_summary
    
    ds_ensembl = ReferenceDatasetSpec("ds1", "D1", "S1", "human", "gene_tpm", "ENSEMBL")
    registry = ReferenceDatasetRegistry(datasets=(ds_ensembl,))
    
    ctx = build_comparator_matching_context(mock_intake, registry)
    
    assert ctx.summary.n_matched_comparisons == 0
    assert len(ctx.unmatched_comparisons) == 1
    assert ctx.unmatched_comparisons[0].reason_codes == ("no_compatible_reference_dataset",)
    assert ctx.summary.is_ready_for_comparison_engine is False # No matches found

def test_matching_readiness_delegation():
    """
    If intake readiness is false, matching context readiness should also be false.
    """
    mock_intake = MagicMock(spec=ComparatorIntakeContext)
    mock_summary = MagicMock()
    mock_summary.is_ready_for_reference_matching = False
    mock_intake.summary = mock_summary
    mock_intake.accepted_comparisons = ()
    
    registry = ReferenceDatasetRegistry(datasets=())
    ctx = build_comparator_matching_context(mock_intake, registry)
    
    assert ctx.summary.is_ready_for_comparison_engine is False
