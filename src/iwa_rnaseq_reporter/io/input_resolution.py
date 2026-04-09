from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass(frozen=True)
class InputResolutionResult:
    """
    Result of resolving user input path into dataset and bundle manifests.
    """
    original_input_path: str
    resolved_dataset_manifest_path: Optional[str] = None
    resolved_bundle_manifest_path: Optional[str] = None
    input_kind: str = "unknown"  # dataset_manifest, bundle_manifest, dataset_dir, unknown
    load_mode: str = "unresolved" # dataset_only, dataset_plus_bundle, bundle_only, unresolved
    resolution_messages: List[str] = field(default_factory=list)

def resolve_reporter_input_paths(input_path_str: str) -> InputResolutionResult:
    """
    Resolves manifest paths from a user-provided input string.
    Does not load data, only resolves paths and determines intent.
    """
    if not input_path_str or not input_path_str.strip():
        return InputResolutionResult(
            original_input_path=input_path_str,
            resolution_messages=["Empty input path."]
        )

    # Normalize path
    original_path = Path(input_path_str)
    # Handle ~ manually if needed, but Path.expanduser is standard
    try:
        norm_path = original_path.expanduser().resolve()
    except Exception as e:
        return InputResolutionResult(
            original_input_path=input_path_str,
            resolution_messages=[f"Path resolution failed: {e}"]
        )

    if not norm_path.exists():
        return InputResolutionResult(
            original_input_path=input_path_str,
            resolution_messages=[f"Path does not exist: {norm_path}"]
        )

    messages = []
    dataset_manifest = None
    bundle_manifest = None
    kind = "unknown"
    mode = "unresolved"

    # Case 1: Directory
    if norm_path.is_dir():
        kind = "dataset_dir"
        messages.append(f"Input treated as directory: {norm_path}")
        
        # Priority 1: results/ subfolder
        res_dir = norm_path / "results"
        if res_dir.exists() and res_dir.is_dir():
            if (res_dir / "dataset_manifest.json").exists():
                dataset_manifest = res_dir / "dataset_manifest.json"
                messages.append("Found dataset manifest in results/ subfolder.")
            if (res_dir / "analysis_bundle_manifest.json").exists():
                bundle_manifest = res_dir / "analysis_bundle_manifest.json"
                messages.append("Found bundle manifest in results/ subfolder.")
        
        # Priority 2: root folder (if not found in results)
        if not dataset_manifest and (norm_path / "dataset_manifest.json").exists():
            dataset_manifest = norm_path / "dataset_manifest.json"
            messages.append("Found dataset manifest in directory root.")
        if not bundle_manifest and (norm_path / "analysis_bundle_manifest.json").exists():
            bundle_manifest = norm_path / "analysis_bundle_manifest.json"
            messages.append("Found bundle manifest in directory root.")

    # Case 2: Specific manifest file
    elif norm_path.is_file():
        if norm_path.name == "dataset_manifest.json":
            kind = "dataset_manifest"
            dataset_manifest = norm_path
            messages.append("Input treated as explicit dataset manifest.")
            # Try to pick up bundle as sibling
            sibling_bundle = norm_path.parent / "analysis_bundle_manifest.json"
            if sibling_bundle.exists():
                bundle_manifest = sibling_bundle
                messages.append("Found sibling bundle manifest.")
                
        elif norm_path.name == "analysis_bundle_manifest.json":
            kind = "bundle_manifest"
            bundle_manifest = norm_path
            messages.append("Input treated as explicit bundle manifest.")
            # Try to pick up dataset as sibling
            sibling_dataset = norm_path.parent / "dataset_manifest.json"
            if sibling_dataset.exists():
                dataset_manifest = sibling_dataset
                messages.append("Found sibling dataset manifest.")
        else:
            messages.append(f"Unrecognized file: {norm_path.name}")

    # Determine load mode
    if dataset_manifest and bundle_manifest:
        mode = "dataset_plus_bundle"
    elif dataset_manifest:
        mode = "dataset_only"
    elif bundle_manifest:
        mode = "bundle_only"
        
    return InputResolutionResult(
        original_input_path=input_path_str,
        resolved_dataset_manifest_path=str(dataset_manifest) if dataset_manifest else None,
        resolved_bundle_manifest_path=str(bundle_manifest) if bundle_manifest else None,
        input_kind=kind,
        load_mode=mode,
        resolution_messages=messages
    )
