from __future__ import annotations

from pathlib import Path

from .io_utils import read_json


def load_manifest(manifest_path: str | Path) -> dict:
    """Load the dataset manifest from a JSON file."""
    return read_json(manifest_path)


def resolve_manifest_paths(manifest: dict, manifest_path: str | Path) -> dict[str, Path]:
    """
    Resolve relative paths in the manifest to absolute paths.
    Tries resolving relative to the manifest directory and its parent (run root).
    Handles both 'paths' (draft) and 'files' (legacy) keys.
    """
    manifest_dir = Path(manifest_path).parent
    run_dir = manifest_dir.parent
    resolved = {}

    # Support both 'paths' (new) and 'files' (legacy)
    path_config = manifest.get("paths") or manifest.get("files") or {}

    for key, rel_path in path_config.items():
        if not rel_path:
            continue

        p = Path(rel_path)
        if p.is_absolute():
            resolved[key] = p
        else:
            # Try a few common resolutions and see what exists
            # 1. Relative to manifest_dir (standard)
            cand1 = (manifest_dir / p).resolve()
            # 2. Relative to run_dir (handles "results/xxx" in manifest at "results/manifest.json")
            cand2 = (run_dir / p).resolve()
            # 3. Just the file name in manifest_dir (handles "results/xxx" when file is actually at same level)
            cand3 = (manifest_dir / p.name).resolve()

            if cand1.exists():
                resolved[key] = cand1
            elif cand2.exists():
                resolved[key] = cand2
            elif cand3.exists():
                resolved[key] = cand3
            else:
                # Default to cand1 so validator can report the missing file with a reasonable path
                resolved[key] = cand1

    return resolved
