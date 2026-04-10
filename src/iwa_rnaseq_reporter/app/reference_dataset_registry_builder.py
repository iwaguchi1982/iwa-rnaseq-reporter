from typing import List
from .reference_dataset_registry import (
    ReferenceDatasetRegistry,
    ReferenceDatasetSpec,
    ReferenceComparisonSpec
)

def build_mock_reference_dataset_registry() -> ReferenceDatasetRegistry:
    """
    Build a small, mock registry for testing and initial development.
    Contains common species and matrix kinds.
    """
    datasets = []
    
    # 1. TCGA-like Liver Cancer Dataset (ENSEMBL / gene_tpm)
    ds1_comparisons = (
        ReferenceComparisonSpec(
            reference_comparison_id="TCGA_LIHC_T_vs_N",
            comparison_label="Liver Hepatocellular Carcinoma: Tumor vs Normal",
            comparison_group_a="Tumor",
            comparison_group_b="Normal",
            result_ref="ref/TCGA_LIHC_T_vs_N_results.json"
        ),
    )
    datasets.append(ReferenceDatasetSpec(
        reference_dataset_id="TCGA_LIHC",
        dataset_label="TCGA Liver Cancer (LIHC)",
        source="TCGA",
        species="human",
        matrix_kind="gene_tpm",
        feature_id_system="ENSEMBL",
        available_comparisons=ds1_comparisons
    ))

    # 2. Mouse Liver Dataset (SYMBOL / gene_tpm)
    ds2_comparisons = (
        ReferenceComparisonSpec(
            reference_comparison_id="MOUSE_LIVER_STZ_vs_CTRL",
            comparison_label="Mouse Liver: STZ-treated vs Control",
            comparison_group_a="STZ",
            comparison_group_b="Control",
            result_ref="ref/MOUSE_L_STZ_results.json"
        ),
    )
    datasets.append(ReferenceDatasetSpec(
        reference_dataset_id="MOUSE_DIABETES",
        dataset_label="Mouse Diabetes Model Liver Results",
        source="Study_A",
        species="mouse",
        matrix_kind="gene_tpm",
        feature_id_system="SYMBOL",
        available_comparisons=ds2_comparisons
    ))

    return ReferenceDatasetRegistry(datasets=tuple(datasets))

def build_reference_dataset_registry(datasets: List[ReferenceDatasetSpec]) -> ReferenceDatasetRegistry:
    """
    General purpose builder from a list of dataset specs.
    """
    return ReferenceDatasetRegistry(datasets=tuple(datasets))
