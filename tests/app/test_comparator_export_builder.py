import pytest
import io
import zipfile
import json
import pandas as pd
from unittest.mock import MagicMock
from iwa_rnaseq_reporter.app.comparator_engine import (
    ComparatorResultContext,
    ComparatorResultSummarySpec,
    ComparatorMatchResultSpec,
    ComparatorScoreSpec,
    ComparatorSkippedMatchSpec
)
from iwa_rnaseq_reporter.app.comparator_export_builder import (
    build_comparator_export_bundle,
    build_comparator_export_payload,
    build_comparator_run_id
)

def test_build_comparator_export_bundle_success():
    # Setup Mock Context
    mock_matching = MagicMock()
    mock_matching.summary.portfolio_id = "p-123"
    mock_matching.summary.accepted_comparison_ids = ["c1", "c2"]
    
    score = ComparatorScoreSpec(100, 50, 0.8, 0.95)
    res1 = ComparatorMatchResultSpec("c1", "ds1", "rc1", "p/c1.csv", "ref/r1.csv", score)
    
    summary = ComparatorResultSummarySpec(2, 1, 1, 1, True)
    skipped = ComparatorSkippedMatchSpec("c2", "ds1", "rc2", ("error",))
    
    ctx = ComparatorResultContext(
        matching_context=mock_matching,
        match_results=(res1,),
        skipped_matches=(skipped,),
        issues=(),
        summary=summary
    )
    
    # RUN
    bundle_bytes = build_comparator_export_bundle(ctx)
    
    # VERIFY ZIP
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        names = zf.namelist()
        assert "comparator_manifest.json" in names
        assert "comparator_handoff_contract.json" in names
        assert "match_results.csv" in names
        assert "report_summary.md" in names
        
        # Verify JSON content
        manifest = json.loads(zf.read("comparator_manifest.json"))
        assert manifest["portfolio_id"] == "p-123"
        assert manifest["n_successful_matches"] == 1
        
        # Verify Handoff Contract
        handoff = json.loads(zf.read("comparator_handoff_contract.json"))
        assert handoff["bundle_refs"]["comparator_manifest_path"] == "comparator_manifest.json" # Relative
        assert "ds1" in handoff["included_reference_dataset_ids"]
        
        # Verify CSV
        csv_content = zf.read("match_results.csv").decode()
        assert "c1,ds1,rc1" in csv_content

def test_build_comparator_export_bundle_zero_matches():
    # Setup Mock Context with 0 successes
    mock_matching = MagicMock()
    mock_matching.summary.portfolio_id = "p-none"
    mock_matching.summary.accepted_comparison_ids = ["c1"]
    
    summary = ComparatorResultSummarySpec(1, 0, 1, 0, False)
    skipped = ComparatorSkippedMatchSpec("c1", "ds1", "rc1", ("missing",))
    
    ctx = ComparatorResultContext(
        matching_context=mock_matching,
        match_results=(),
        skipped_matches=(skipped,),
        issues=(),
        summary=summary
    )
    
    # RUN
    bundle_bytes = build_comparator_export_bundle(ctx)
    
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        names = zf.namelist()
        assert "comparator_manifest.json" in names
        assert "skipped_matches.json" in names
        assert "match_results.csv" not in names # No rows, no CSV (or empty CSV depends on impl)
        
        manifest = json.loads(zf.read("comparator_manifest.json"))
        assert manifest["n_successful_matches"] == 0
        
        summary_md = zf.read("report_summary.md").decode()
        assert "No successful matches" in summary_md
