import pytest
from unittest.mock import MagicMock, patch
from iwa_rnaseq_reporter.io.bundle_loader import load_reporter_analysis_bundle
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle

def test_load_reporter_analysis_bundle_success():
    # Mock return value for summarize_analysis_bundle_for_consumer
    mock_summary = {
        "run_id": "RUN_001",
        "matrix_id": "MATRIX_001",
        "analysis_bundle_manifest_path": "/path/to/manifest.json",
        "contract_name": "analysis_bundle",
        "contract_version": "1.0.0",
        "bundle_kind": "rna_seq_analysis_bundle",
        "producer": "iwa-rnaseq-counter",
        "producer_version": "0.11.4",
        "matrix_shape": {"feature_count": 100, "sample_count": 10},
        "sample_axis": "specimen",
        "feature_id_system": "ensembl_gene_id",
        "column_order_specimen_ids": ["S1", "S2"],
        "source_quantifier_summary": {"tool": "salmon"},
        "feature_annotation_status": None,
        "sample_metadata_alignment_status": None,
        "warning_summary": None
    }
    
    with patch("iwa_rnaseq_reporter.io.bundle_loader.read_analysis_bundle") as mock_read:
        with patch("iwa_rnaseq_reporter.io.bundle_loader.summarize_analysis_bundle_for_consumer") as mock_summarize:
            mock_read.return_value = {"dummy": "bundle"}
            mock_summarize.return_value = mock_summary
            
            result = load_reporter_analysis_bundle("/path/to/manifest.json")
            
            assert isinstance(result, ReporterAnalysisBundle)
            assert result.run_id == "RUN_001"
            assert result.matrix_id == "MATRIX_001"
            assert result.matrix_shape["feature_count"] == 100
            mock_read.assert_called_once_with("/path/to/manifest.json")
            mock_summarize.assert_called_once()

@pytest.mark.parametrize("invalid_path", ["", " ", "  \t  "])
def test_load_reporter_analysis_bundle_invalid_input(invalid_path):
    with pytest.raises(ValueError, match="manifest_path cannot be empty or whitespace only."):
        load_reporter_analysis_bundle(invalid_path)

def test_load_reporter_analysis_bundle_failure_propagation():
    with patch("iwa_rnaseq_reporter.io.bundle_loader.read_analysis_bundle") as mock_read:
        mock_read.side_effect = Exception("Original Error")
        
        with pytest.raises(RuntimeError) as excinfo:
            load_reporter_analysis_bundle("/path/to/manifest.json")
        
        assert "Failed to load reporter analysis bundle from manifest" in str(excinfo.value)
        # Verify original exception is preserved in __cause__
        assert str(excinfo.value.__cause__) == "Original Error"

if __name__ == "__main__":
    # Smoke run if pytest is not used directly
    import sys
    test_load_reporter_analysis_bundle_success()
    try:
        test_load_reporter_analysis_bundle_invalid_input("")
    except ValueError:
        pass
    print("test_bundle_loader smoke tests: PASSED")
