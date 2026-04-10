import io
import json
import zipfile
from typing import Any, Dict
from .comparison_portfolio_handoff import ComparisonPortfolioHandoffPayload
from .deg_handoff_contract import DegHandoffPayload

class ComparatorBundleReader:
    """
    Reader class to extract and deserialize typed specifications from a Portfolio ZIP bundle.
    """
    def __init__(self, bundle_bytes: bytes):
        self._bundle_bytes = bundle_bytes
        # Verify it's a valid ZIP
        try:
            with zipfile.ZipFile(io.BytesIO(self._bundle_bytes)) as zf:
                self._namelist = zf.namelist()
        except zipfile.BadZipFile:
            raise ValueError("Provided bytes are not a valid ZIP archive.")

    def read_json(self, path: str) -> Dict[str, Any]:
        """
        Read a JSON file from the bundle.
        """
        if path not in self._namelist:
            raise FileNotFoundError(f"File '{path}' not found in bundle.")
        
        with zipfile.ZipFile(io.BytesIO(self._bundle_bytes)) as zf:
            with zf.open(path) as f:
                return json.load(f)

    def load_portfolio_handoff(self) -> ComparisonPortfolioHandoffPayload:
        """
        Load the root portfolio handoff contract.
        """
        path = "portfolio_handoff_contract.json"
        data = self.read_json(path)
        return ComparisonPortfolioHandoffPayload.from_dict(data)

    def load_deg_handoff(self, path: str) -> DegHandoffPayload:
        """
        Load a specific DEG comparison handoff contract.
        """
        data = self.read_json(path)
        return DegHandoffPayload.from_dict(data)

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in the bundle.
        """
        return path in self._namelist
