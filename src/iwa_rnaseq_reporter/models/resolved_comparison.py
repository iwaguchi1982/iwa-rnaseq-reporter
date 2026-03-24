from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SampleMetadataRow:
    specimen_id: str
    subject_id: str
    visit_id: Optional[str] = None
    sample_name: Optional[str] = None
    group_labels: Optional[str] = None
    timepoint_label: Optional[str] = None
    batch_label: Optional[str] = None
    pairing_id: Optional[str] = None
    include_flag: bool = True
    note: Optional[str] = None
    extra: Dict[str, object] = field(default_factory=dict)

@dataclass
class ResolvedComparisonPlan:
    comparison_id: str
    input_matrix_id: str
    comparison_type: str
    analysis_intent: str

    group_a_label: str
    group_a_specimen_ids: List[str]

    group_b_label: str
    group_b_specimen_ids: List[str]

    paired: bool = False
    covariates: List[str] = field(default_factory=list)

    group_a_subject_ids: List[str] = field(default_factory=list)
    group_b_subject_ids: List[str] = field(default_factory=list)

    group_a_matrix_columns: List[str] = field(default_factory=list)
    group_b_matrix_columns: List[str] = field(default_factory=list)

    sample_axis: str = "specimen"
    feature_type: str = "gene"
    normalization: str = "raw"
    matrix_path: Optional[str] = None
    feature_annotation_path: Optional[str] = None
    sample_metadata_path: Optional[str] = None

    included_specimen_ids: List[str] = field(default_factory=list)
    excluded_specimen_ids: List[str] = field(default_factory=list)

    metadata: Dict[str, object] = field(default_factory=dict)
