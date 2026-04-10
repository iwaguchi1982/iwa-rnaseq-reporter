from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class ReferenceComparisonSpec:
    """
    Metadata for a specific comparison (contrast) within a reference dataset.
    Example: 'Tumor vs Normal' or 'Responders vs Non-responders'.
    """
    reference_comparison_id: str
    comparison_label: str
    comparison_group_a: str
    comparison_group_b: str
    result_ref: str  # Pointer to actual result data (e.g., file path or ID)

@dataclass(frozen=True)
class ReferenceDatasetSpec:
    """
    Identity and global metadata for a reference dataset.
    """
    reference_dataset_id: str
    dataset_label: str
    source: str
    species: str
    matrix_kind: str
    feature_id_system: str
    available_comparisons: Tuple[ReferenceComparisonSpec, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ReferenceDatasetRegistry:
    """
    A collection of reference datasets available for matching.
    """
    datasets: Tuple[ReferenceDatasetSpec, ...] = field(default_factory=tuple)
