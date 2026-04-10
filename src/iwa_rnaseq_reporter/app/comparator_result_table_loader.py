import io
import pandas as pd
import zipfile
from typing import Optional
from .reference_dataset_registry import ReferenceComparisonSpec

class ComparatorResultTableLoader:
    """
    Handles loading of DEG result tables from both the experimental portfolio bundle
    and resolved reference pointers.
    """
    def __init__(self, bundle_bytes: bytes):
        self._bundle_bytes = bundle_bytes

    def load_experimental_result_table(self, comparison_id: str) -> pd.DataFrame:
        """
        Extract comparisons/<id>/deg_results.csv from the portfolio bundle.
        """
        path = f"comparisons/{comparison_id}/deg_results.csv"
        try:
            with zipfile.ZipFile(io.BytesIO(self._bundle_bytes)) as zf:
                if path not in zf.namelist():
                    raise FileNotFoundError(f"Result table not found for {comparison_id}")
                with zf.open(path) as f:
                    return pd.read_csv(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load experimental table for {comparison_id}: {e}")

    def load_reference_result_table(self, ref_comp: ReferenceComparisonSpec) -> pd.DataFrame:
        """
        Resolve and load the reference result table.
        For now, this supports simple file path resolution (mocked/local).
        """
        path = ref_comp.result_ref
        try:
            # In a real system, this might fetch from a database or S3.
            # For v0.17.3, we assume it's a resolveable local path or fixture.
            return pd.read_csv(path)
        except Exception as e:
            raise RuntimeError(f"Failed to load reference table from {path}: {e}")

def validate_result_table_columns(df: pd.DataFrame) -> bool:
    """
    Check if the DataFrame has necessary columns: feature_id, log2_fc, padj.
    """
    required = {"feature_id", "log2_fc", "padj"}
    return required.issubset(df.columns)
