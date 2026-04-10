from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path

@dataclass(frozen=True)
class ConsensusBundleValidationIssueSpec:
    """
    Representation of a single problem found during bundle validation.
    """
    level: str  # "error" | "warning"
    code: str
    message: str
    artifact_name: Optional[str] = None
    path: Optional[str] = None
    field_name: Optional[str] = None

@dataclass(frozen=True)
class ConsensusBundleContractInfo:
    """
    Compatibility metadata extracted from manifest and handoff.
    """
    schema_name: str
    schema_version: str
    handoff_schema_name: Optional[str]
    handoff_schema_version: Optional[str]
    is_supported: bool
    compatibility_status: str

@dataclass(frozen=True)
class ConsensusBundlePaths:
    """
    Resolved absolute paths to components of the consensus bundle.
    """
    manifest_path: Path
    bundle_root: Path
    handoff_contract_path: Optional[Path] = None
    summary_path: Optional[Path] = None
    results_table_path: Optional[Path] = None
    # v0.19.2a added slots for internal JSONs if needed
    decisions_json_path: Optional[Path] = None
    evidence_profiles_path: Optional[Path] = None
    optional_paths: Dict[str, Path] = field(default_factory=dict)

@dataclass(frozen=True)
class ConsensusBundleImportContext:
    """
    Complete collection of data loaded from a valid consensus bundle.
    """
    manifest: Dict[str, Any]
    handoff_contract: Optional[Dict[str, Any]]
    paths: ConsensusBundlePaths
    contract_info: ConsensusBundleContractInfo
    # v0.19.2a Data slots
    summary_markdown: Optional[str] = None
    results_table: Optional[Any] = None  # Expected pd.DataFrame
    decisions_json: Optional[Union[Dict[str, Any], Tuple[Dict[str, Any], ...]]] = None
    evidence_profiles_json: Optional[Union[Dict[str, Any], Tuple[Dict[str, Any], ...]]] = None
    # Legacy slots
    decisions: Tuple[Any, ...] = field(default_factory=tuple)
    summary: Optional[Any] = None

@dataclass(frozen=True)
class ConsensusBundleValidationResult:
    """
    Diagnostic results of a bundle validation attempt.
    """
    manifest_path: Path
    bundle_root: Path
    contract_info: ConsensusBundleContractInfo
    is_valid: bool
    error_count: int
    warning_count: int
    issues: Tuple[ConsensusBundleValidationIssueSpec, ...]
    resolved_artifacts: Tuple[str, ...] = field(default_factory=tuple)
