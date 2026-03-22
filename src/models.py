from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class ValidationMessage:
    level: Literal["fatal", "warning", "info"]
    code: str
    message: str


@dataclass
class ReporterDataset:
    dataset_id: str
    run_name: str
    input_type: str  # "manifest" | "run_dir" | "results_dir" | "unknown"
    manifest_path: Path
    base_dir: Path
    results_dir: Path
    manifest: dict
    run_summary: dict

    sample_metadata: pd.DataFrame
    sample_qc_summary: pd.DataFrame
    gene_tpm: pd.DataFrame
    gene_numreads: pd.DataFrame
    transcript_tpm: pd.DataFrame | None = None
    transcript_numreads: pd.DataFrame | None = None
    resolved_paths: dict[str, Path] = field(default_factory=dict)

    sample_ids_all: list[str] = field(default_factory=list)
    sample_ids_success: list[str] = field(default_factory=list)
    sample_ids_failed: list[str] = field(default_factory=list)
    sample_ids_aggregated: list[str] = field(default_factory=list)

    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def has_fatal(self) -> bool:
        return any(m.level == "fatal" for m in self.messages)

    @property
    def has_warning(self) -> bool:
        return any(m.level == "warning" for m in self.messages)

    # For legacy compatibility with draft specs
    @property
    def app_name(self) -> str:
        return self.manifest.get("app_name", "")

    @property
    def app_version(self) -> str:
        return self.manifest.get("app_version", "")

    @property
    def analysis_name(self) -> str:
        return self.manifest.get("analysis_name", self.run_name)
