import pytest
import os
import zipfile
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from iwa_rnaseq_reporter.app.comparator_consensus import (
    ComparatorConsensusContext,
    ConsensusDecisionSpec,
    ConsensusEvidenceProfileSpec,
    ComparatorConsensusSummarySpec
)
from iwa_rnaseq_reporter.app.comparator_consensus_export_builder import (
    build_consensus_export_payload,
    build_consensus_export_bundle,
    build_consensus_run_id
)
from iwa_rnaseq_reporter.app.comparator_consensus_handoff_builder import (
    build_consensus_handoff_payload,
    serialize_handoff_contract
)
from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import read_consensus_bundle

def test_consensus_export_import_roundtrip():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # 1. Setup Mock Consensus Data
        dec = ConsensusDecisionSpec("cid1", "consensus", "L1", "Label 1", ())
        prof = ConsensusEvidenceProfileSpec("cid1", None, (), (), (), 0.5, False, False)
        summary = ComparatorConsensusSummarySpec(1, 1, 0, 0, 0, True)
        
        # Use a mock for ranking_context as it's not direct output
        from unittest.mock import MagicMock
        ctx = ComparatorConsensusContext(
            ranking_context=MagicMock(),
            decisions=(dec,),
            evidence_profiles=(prof,),
            issues=(),
            summary=summary
        )
        
        # 2. Export
        run_id = "roundtrip_run"
        # Force a single timestamp for roundtrip verification if needed, 
        # but here we test the builder's own timestamp generation
        payload = build_consensus_export_payload(ctx, run_id)
        handoff = build_consensus_handoff_payload(ctx, payload, "bundle.zip")
        handoff_json = serialize_handoff_contract(handoff)
        
        bundle_bytes = build_consensus_export_bundle(payload, handoff_json)
        
        # 3. Simulate Bundle Extraction (or entry point)
        # We'll write the bundle to a directory to use our dir-based reader
        with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
            zf.extractall(root)
            
        # 4. Import
        import_ctx = read_consensus_bundle(root)
        
        # 5. Compare manifest identity
        assert import_ctx.manifest["consensus_run_id"] == run_id
        assert import_ctx.manifest["schema_name"] == "ConsensusExportManifest"
        assert import_ctx.manifest["schema_version"] == "0.19.1"
        assert import_ctx.manifest["n_consensus"] == 1
        
        # 6. Compare provenance
        assert import_ctx.manifest["provenance"]["producer_app"] == "iwa_rnaseq_reporter"
        assert import_ctx.manifest["provenance"]["source_consensus_run_id"] == run_id
        
        # 7. Compare handoff
        assert import_ctx.handoff_contract["consensus_run_id"] == run_id
        assert import_ctx.handoff_contract["schema_name"] == "ConsensusHandoffContract"
        
        # Verify Paths
        assert import_ctx.paths.manifest_path.exists()
        assert import_ctx.paths.handoff_contract_path.exists()
        assert import_ctx.paths.summary_path.exists()
