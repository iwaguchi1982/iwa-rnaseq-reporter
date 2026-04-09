from typing import Optional, Any
from iwa_rnaseq_reporter.io.input_resolution import resolve_reporter_input_paths
from iwa_rnaseq_reporter.io.bundle_loader import load_reporter_analysis_bundle
from iwa_rnaseq_reporter.legacy.loader import load_reporter_dataset, ReporterLoadError
from iwa_rnaseq_reporter.app.resolved_input_context import ResolvedInputContext
from iwa_rnaseq_reporter.app.reporter_session_context import ReporterSessionContext
from iwa_rnaseq_reporter.models.analysis_bundle_view_model import ReporterAnalysisBundle, BundleDiagnostic

def _try_load_bundle(input_path_str: str) -> tuple[Optional[ReporterAnalysisBundle], Optional[BundleDiagnostic]]:
    """
    Attempt to load analysis bundle and return result with diagnostics.
    Original implementation moved from app.py.
    """
    try:
        bundle = load_reporter_analysis_bundle(input_path_str)
        
        # Determine diagnostic status
        warning_flags = []
        if bundle.warning_summary:
            warning_flags.append("Bundle has internal warnings.")
        
        alignment = bundle.sample_metadata_alignment_status
        if alignment and not alignment.get("is_aligned", True):
            warning_flags.append("Sample metadata may be misaligned.")
            
        if warning_flags:
            diag = BundleDiagnostic(
                status="warning",
                user_message="Analysis Bundle loaded with warnings.",
                technical_message=f"Warnings detected: {', '.join(warning_flags)}",
                warning_flags=warning_flags,
                manifest_path=input_path_str
            )
        else:
            diag = BundleDiagnostic(
                status="ok",
                user_message="Analysis Bundle loaded successfully.",
                manifest_path=input_path_str
            )
        return bundle, diag
        
    except Exception as e:
        return None, BundleDiagnostic(
            status="error",
            user_message="Analysis Bundle metadata is not available.",
            technical_message=str(e),
            manifest_path=input_path_str
        )

def load_reporter_entry_state(input_path_str: str) -> ReporterSessionContext:
    """
    Orchestrate the entry flow: resolution, dataset load, bundle ingest, and diagnostic.
    Returns a unified ReporterSessionContext.
    Does NOT depend on Streamlit.
    """
    # 1. Resolve input paths
    resolution = resolve_reporter_input_paths(input_path_str)
    res_ctx = ResolvedInputContext.from_resolution_result(resolution)
    
    if res_ctx.is_unresolved:
        return ReporterSessionContext(resolved_input_context=res_ctx)

    ds = None
    bundle = None
    diag = None

    # 2. Try load dataset if resolved
    if res_ctx.has_dataset_manifest:
        try:
            ds = load_reporter_dataset(res_ctx.resolved_dataset_manifest_path)
        except ReporterLoadError:
            # We let the caller handle reporting, but we capture what we have
            return ReporterSessionContext(resolved_input_context=res_ctx)
        except Exception:
            return ReporterSessionContext(resolved_input_context=res_ctx)

    # 3. Try load bundle if resolved
    if res_ctx.has_bundle_manifest:
        bundle, diag = _try_load_bundle(res_ctx.resolved_bundle_manifest_path)
    
    # 4. Build session context
    return ReporterSessionContext.from_parts(
        resolved_input_context=res_ctx,
        dataset=ds,
        analysis_bundle=bundle,
        analysis_bundle_diagnostic=diag
    )
