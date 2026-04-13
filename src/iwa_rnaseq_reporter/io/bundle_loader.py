from typing import Any, Dict, List, Optional
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle

# Deferred imports to avoid hard dependency on the counter package at startup.
# This allows the reporter to start even if the counter is not installed.
try:
    from iwa_rnaseq_counter.io.read_analysis_bundle import (
        read_analysis_bundle,
        summarize_analysis_bundle_for_consumer
    )
except ImportError:
    # Stubs for environments without the counter package.
    # We define them as None so that unittest.mock.patch can still target these names.
    read_analysis_bundle = None
    summarize_analysis_bundle_for_consumer = None

def load_reporter_analysis_bundle(manifest_path: str) -> ReporterAnalysisBundle:
    """
    Loads an Analysis Bundle from a manifest path and converts it to a ReporterAnalysisBundle.
    
    Args:
        manifest_path: Path to the analysis bundle manifest.
    
    Returns:
        A ReporterAnalysisBundle populated with verified metadata.
        
    Raises:
        ValueError: If manifest_path is empty or whitespace.
        RuntimeError: If the counter package is missing or the bundle cannot be loaded.
    """
    if not manifest_path or not manifest_path.strip():
        raise ValueError("manifest_path cannot be empty or whitespace only.")

    if read_analysis_bundle is None or summarize_analysis_bundle_for_consumer is None:
        raise RuntimeError(
            "The 'iwa-rnaseq-counter' package is required to load analysis bundles, "
            "but it is not installed in the current environment."
        )

    try:
        # Load the bundle using the Counter's public API
        bundle = read_analysis_bundle(manifest_path)
        
        # Summarize the bundle using the Counter's public summary helper
        summary = summarize_analysis_bundle_for_consumer(bundle)
        
        # Clean up summary to handle missing fields gracefully
        # If run_id is None, letting the ReporterAnalysisBundle default handle it 
        # (or provide it here explicitly)
        if summary.get("run_id") is None:
            summary["run_id"] = "UNKNOWN"
            
        return ReporterAnalysisBundle(**{k: v for k, v in summary.items() if v is not None})
        
    except Exception as e:
        raise RuntimeError(
            f"Failed to load reporter analysis bundle from manifest: {manifest_path}"
        ) from e
