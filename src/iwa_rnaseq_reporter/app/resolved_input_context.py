from dataclasses import dataclass
from typing import Optional, List, Tuple
from ..io.input_resolution import InputResolutionResult

@dataclass(frozen=True)
class ResolvedInputContext:
    """
    Application-level context for a resolved input path.
    Used to track what manifests were identified and how they should be loaded.
    """
    original_input_path: str
    resolved_dataset_manifest_path: Optional[str]
    resolved_bundle_manifest_path: Optional[str]
    input_kind: str
    load_mode: str
    resolution_messages: Tuple[str, ...]

    @property
    def has_dataset_manifest(self) -> bool:
        return self.resolved_dataset_manifest_path is not None

    @property
    def has_bundle_manifest(self) -> bool:
        return self.resolved_bundle_manifest_path is not None

    @property
    def is_unresolved(self) -> bool:
        return self.load_mode == "unresolved"

    @classmethod
    def from_resolution_result(cls, res: InputResolutionResult) -> "ResolvedInputContext":
        """
        Creates a context from a raw resolution result.
        """
        return cls(
            original_input_path=res.original_input_path,
            resolved_dataset_manifest_path=res.resolved_dataset_manifest_path,
            resolved_bundle_manifest_path=res.resolved_bundle_manifest_path,
            input_kind=res.input_kind,
            load_mode=res.load_mode,
            resolution_messages=tuple(res.resolution_messages)
        )

    def to_display_dict(self) -> dict:
        """
        Returns a dictionary suitable for UI display.
        """
        return {
            "Original Input": self.original_input_path,
            "Input Kind": self.input_kind,
            "Load Mode": self.load_mode,
            "Dataset Manifest": self.resolved_dataset_manifest_path or "None",
            "Bundle Manifest": self.resolved_bundle_manifest_path or "None"
        }
