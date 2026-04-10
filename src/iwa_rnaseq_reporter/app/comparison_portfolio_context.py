from dataclasses import dataclass, field
from typing import Tuple, List
from iwa_rnaseq_reporter.app.deg_export_spec import DegExportPayload
from iwa_rnaseq_reporter.app.deg_handoff_contract import DegHandoffPayload
from iwa_rnaseq_reporter.app.deg_result_context import DegSummaryMetrics

@dataclass(frozen=True)
class ComparisonRecord:
    """
    A single record of a DEG comparison result and its associated artifacts.
    Held within a ComparisonPortfolioContext.
    """
    comparison_id: str
    comparison_label: str
    export_payload: DegExportPayload
    handoff_payload: DegHandoffPayload
    bundle_filename: str
    summary_metrics: DegSummaryMetrics


@dataclass(frozen=True)
class ComparisonPortfolioContext:
    """
    A collection of ComparisonRecords within a single session or project workspace.
    """
    portfolio_id: str
    records: Tuple[ComparisonRecord, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.records)

    @property
    def comparison_ids(self) -> List[str]:
        return [r.comparison_id for r in self.records]
