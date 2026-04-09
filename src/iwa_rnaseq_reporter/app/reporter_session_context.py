from dataclasses import dataclass, replace
from typing import Optional, Any
from .resolved_input_context import ResolvedInputContext
from ..models.analysis_bundle_view_model import ReporterAnalysisBundle, BundleDiagnostic

@dataclass(frozen=True)
class ReporterSessionContext:
    """
    Reporter の入口状態を束ねる Context。
    Streamlit 依存を排除した pure な dataclass。
    """
    resolved_input_context: Optional[ResolvedInputContext] = None
    dataset: Optional[Any] = None
    analysis_bundle: Optional[ReporterAnalysisBundle] = None
    analysis_bundle_diagnostic: Optional[BundleDiagnostic] = None

    @property
    def has_resolved_input(self) -> bool:
        return self.resolved_input_context is not None

    @property
    def has_dataset(self) -> bool:
        return self.dataset is not None

    @property
    def has_analysis_bundle(self) -> bool:
        return self.analysis_bundle is not None

    @property
    def has_bundle_diagnostic(self) -> bool:
        return self.analysis_bundle_diagnostic is not None

    @property
    def is_dataset_ready(self) -> bool:
        return self.has_dataset

    @property
    def is_bundle_ready(self) -> bool:
        return (
            self.has_analysis_bundle and 
            self.has_bundle_diagnostic and 
            self.analysis_bundle_diagnostic.status in ["ok", "warning"]
        )

    @property
    def is_dataset_only_mode(self) -> bool:
        return self.has_dataset and not self.has_analysis_bundle

    @property
    def is_bundle_warning(self) -> bool:
        return (
            self.has_bundle_diagnostic and 
            self.analysis_bundle_diagnostic.status == "warning"
        )

    @property
    def is_bundle_error(self) -> bool:
        return (
            self.has_bundle_diagnostic and 
            self.analysis_bundle_diagnostic.status == "error"
        )

    @classmethod
    def from_parts(
        cls,
        resolved_input_context: Optional[ResolvedInputContext] = None,
        dataset: Optional[Any] = None,
        analysis_bundle: Optional[ReporterAnalysisBundle] = None,
        analysis_bundle_diagnostic: Optional[BundleDiagnostic] = None,
    ) -> "ReporterSessionContext":
        """
        パーツから Context を生成する helper。
        """
        return cls(
            resolved_input_context=resolved_input_context,
            dataset=dataset,
            analysis_bundle=analysis_bundle,
            analysis_bundle_diagnostic=analysis_bundle_diagnostic,
        )

    def update(self, **kwargs) -> "ReporterSessionContext":
        """
        現在の Context をベースに一部のフィールドを更新した新しい Context を返す。
        """
        return replace(self, **kwargs)
