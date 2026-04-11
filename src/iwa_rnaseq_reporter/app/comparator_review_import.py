from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from .comparator_review_export import (
    ComparatorReviewExportManifestSpec,
    ComparatorReviewExportRowSpec,
    ComparatorReviewSummarySpec
)
from .comparator_review_handoff import ComparatorReviewHandoffPayload

@dataclass(frozen=True)
class ComparatorReviewImportPaths:
    """Relative paths for the imported review bundle artifacts."""
    manifest: str
    handoff_contract: str
    rows_json: str
    rows_csv: str
    summary_json: str
    summary_md: str

@dataclass(frozen=True)
class ComparatorReviewImportContext:
    """Read-only context for an imported review bundle."""
    manifest: ComparatorReviewExportManifestSpec
    handoff_contract: ComparatorReviewHandoffPayload
    review_rows: Tuple[ComparatorReviewExportRowSpec, ...]
    summary: ComparatorReviewSummarySpec
    summary_md: str
    paths: ComparatorReviewImportPaths
    provenance: Dict[str, Any] = field(default_factory=dict)
    issues: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0
