from typing import Any, Dict, List, Optional
from iwa_rnaseq_counter.io.read_analysis_bundle import (
    read_analysis_bundle,
    summarize_analysis_bundle_for_consumer
)
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle

def load_reporter_analysis_bundle(manifest_path: str) -> ReporterAnalysisBundle:
    """
    Loads an Analysis Bundle from a manifest path and converts it to a ReporterAnalysisBundle.
    
    Args:
        manifest_path: Path to the analysis bundle manifest.
    
    Returns:
        A ReporterAnalysisBundle populated with verified metadata.
        
    Raises:
        ValueError: If manifest_path is empty or whitespace.
        RuntimeError: If the bundle cannot be loaded or summarized.
    """
    if not manifest_path or not manifest_path.strip():
        raise ValueError("manifest_path cannot be empty or whitespace only.")

    try:
        # Load the bundle using the Counter's public API
        bundle = read_analysis_bundle(manifest_path)
        
        # Summarize the bundle using the Counter's public summary helper
        # This summary is the source of truth for the Reporter Handoff Profile.
        summary = summarize_analysis_bundle_for_consumer(bundle)
        
        # Instantiate the Reporter-side view model
        # We use unpacking here because the keys in summarize_analysis_bundle_for_consumer
        # are intentionally aligned with the ReporterAnalysisBundle dataclass.
        return ReporterAnalysisBundle(**summary)
        
    except Exception as e:
        # Wrap the original exception to provide context for the reporter
        raise RuntimeError(
            f"Failed to load reporter analysis bundle from manifest: {manifest_path}"
        ) from e
