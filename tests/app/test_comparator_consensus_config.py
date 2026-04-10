import pytest
import json
import dataclasses
from pathlib import Path
from tempfile import TemporaryDirectory
from iwa_rnaseq_reporter.app.comparator_execution_config import (
    RankingConfigSpec,
    ConsensusDecisionConfigSpec,
    build_default_comparator_execution_config
)
from iwa_rnaseq_reporter.app.comparator_ranking_builder import (
    compute_integrated_ranking_score,
    rank_references_for_comparison
)
from iwa_rnaseq_reporter.app.comparator_consensus_builder import build_consensus_decision
from iwa_rnaseq_reporter.app.comparator_consensus_import_builder import validate_consensus_bundle

def test_default_config_values():
    exec_cfg = build_default_comparator_execution_config()
    assert exec_cfg.ranking.overlap_weight == 0.20
    assert exec_cfg.ranking.tie_tolerance == 0.02
    assert exec_cfg.consensus.consensus_margin_threshold == 0.05

def test_custom_ranking_weights():
    from iwa_rnaseq_reporter.app.comparator_ranking_input import ComparatorNormalizedScoreSpec
    
    score = ComparatorNormalizedScoreSpec(1.0, 1.0, 1.0, 1.0)
    
    # Default: 0.2 + 0.3 + 0.2 + 0.3 = 1.0
    s_default = compute_integrated_ranking_score(score)
    assert s_default.integrated_score == 1.0
    
    # Custom: All zeros but one
    custom_cfg = RankingConfigSpec(overlap_weight=1.0, concordance_weight=0.0, correlation_weight=0.0, top_n_overlap_weight=0.0)
    score_only_overlap = ComparatorNormalizedScoreSpec(0.5, 0.0, 0.0, 0.0)
    s_custom = compute_integrated_ranking_score(score_only_overlap, config=custom_cfg)
    assert s_custom.integrated_score == 0.5

def test_custom_consensus_margin():
    from iwa_rnaseq_reporter.app.comparator_consensus import (
        ConsensusEvidenceProfileSpec, 
        ConsensusLabelCandidateSpec,
        ConsensusDecisionSpec
    )
    
    # Candidate 1: 0.5, Candidate 2: 0.46 -> Margin 0.04
    top = ConsensusLabelCandidateSpec("cid", "L1", "Label 1", 1, 0.50, 0.50)
    comp = ConsensusLabelCandidateSpec("cid", "L2", "Label 2", 1, 0.46, 0.46)
    
    profile = ConsensusEvidenceProfileSpec(
        comparison_id="cid",
        top_candidate=top,
        competing_candidates=(comp,),
        supporting_references=(),
        conflicting_references=(),
        support_margin=0.04,
        has_conflict=True,
        has_weak_support=False
    )
    
    # Default margin threshold is 0.05 -> Should be "no_consensus"
    d_default = build_consensus_decision(profile, False)
    assert d_default.decision_status == "no_consensus"
    
    # Custom margin threshold 0.03 -> Should be "consensus"
    custom_cfg = ConsensusDecisionConfigSpec(consensus_margin_threshold=0.03)
    d_custom = build_consensus_decision(profile, False, consensus_config=custom_cfg)
    assert d_custom.decision_status == "consensus"

def test_validator_detects_missing_config():
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        
        # Valid-ish manifest but missing execution_config
        manifest = {
            "schema_name": "ConsensusExportManifest",
            "schema_version": "0.19.3",
            "consensus_run_id": "r1",
            "generated_at": "2026-04-10T12:00:00Z",
            "n_ranked_comparisons": 0, "n_consensus": 0, "n_abstain": 0, "n_no_consensus": 0, "n_insufficient_evidence": 0,
            "provenance": {"producer_app": "a", "producer_version": "v1", "source_consensus_run_id": "r1"}
            # execution_config is missing
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
            
        result = validate_consensus_bundle(manifest_path)
        codes = [i.code for i in result.issues]
        assert "missing_required_field" in codes
        # The specific field name should be execution_config
        fields = [i.field_name for i in result.issues if i.code == "missing_required_field"]
        assert "execution_config" in fields

def test_status_enum_stability():
    """
    Ensure custom policy strings in config DO NOT pollute decision_status enum.
    Corresponds to spec 6-1.
    """
    from iwa_rnaseq_reporter.app.comparator_consensus import (
        ConsensusEvidenceProfileSpec, 
        ConsensusLabelCandidateSpec,
        ConsensusDecisionSpec
    )
    
    # 1. Top Rank Conflict case
    top = ConsensusLabelCandidateSpec("cid", "L1", "Label 1", 1, 0.50, 0.50)
    profile = ConsensusEvidenceProfileSpec(
        "cid", top, (), (), (), 0.5, False, False
    )
    
    # Custom config with "weird" policies
    custom_cfg = ConsensusDecisionConfigSpec(
        top_rank_conflict_policy="WEIRD_CONFLICT_STATUS",
        insufficient_support_policy="WHATEVER"
    )
    
    # Even if policy says "WEIRD_CONFLICT_STATUS", final status must be "no_consensus"
    d_conflict = build_consensus_decision(profile, True, consensus_config=custom_cfg)
    assert d_conflict.decision_status == "no_consensus"
    assert "top_rank_conflict_present" in d_conflict.reason_codes
    
    # 2. Insufficient Support case
    # No top candidate -> must be "insufficient_evidence" despite policy
    empty_profile = ConsensusEvidenceProfileSpec(
        "cid", None, (), (), (), None, False, False
    )
    d_insufficient = build_consensus_decision(empty_profile, False, consensus_config=custom_cfg)
    assert d_insufficient.decision_status == "insufficient_evidence"
    assert "no_ranked_matches" in d_insufficient.reason_codes

def test_validator_required_config_fields():
    """
    Ensure validator requires config_source, top_n_overlap_weight, etc.
    Corresponds to spec 6-2.
    """
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        manifest_path = root / "consensus_manifest.json"
        
        # Manifest with INCOMPLETE execution_config
        manifest = {
            "schema_name": "ConsensusExportManifest", "schema_version": "0.19.3",
            "consensus_run_id": "r1", "generated_at": "2026-04-10T12:00:00Z",
            "n_ranked_comparisons": 0, "n_consensus": 0, "n_abstain": 0, "n_no_consensus": 0, "n_insufficient_evidence": 0,
            "provenance": {"producer_app": "a", "producer_version": "v1", "source_consensus_run_id": "r1"},
            "execution_config": {
                "config_name": "Test", "config_version": "1.0",
                # "config_source": "MISSING", 
                "ranking": {
                    "overlap_weight": 0.2, "concordance_weight": 0.3, "correlation_weight": 0.2, "tie_tolerance": 0.02
                    # "top_n_overlap_weight": "MISSING", "exact_tie_epsilon": "MISSING"
                },
                "consensus": {
                    "consensus_margin_threshold": 0.05, "minimum_supporting_references": 1, "weak_support_mean_threshold": 0.3
                    # "top_rank_conflict_policy": "MISSING", etc
                }
            }
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
            
        result = validate_consensus_bundle(manifest_path)
        issues = result.issues
        codes = [i.code for i in issues]
        fields = [i.field_name for i in issues if i.field_name]
        
        # Missing config_source (Top-level)
        assert any("config_source" in f for f in fields)
        # Missing top_n_overlap_weight (Ranking)
        assert any("top_n_overlap_weight" in f for f in fields)
        # Missing top_rank_conflict_policy (Consensus)
        assert any("top_rank_conflict_policy" in f for f in fields)
