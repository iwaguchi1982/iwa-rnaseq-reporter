import uuid
from typing import Optional, List
from iwa_rnaseq_reporter.app.deg_result_context import DegResultContext
from iwa_rnaseq_reporter.app.deg_export_spec import DegExportPayload
from iwa_rnaseq_reporter.app.deg_handoff_contract import DegHandoffPayload
from .comparison_portfolio_context import ComparisonRecord, ComparisonPortfolioContext

def build_comparison_record(
    context: DegResultContext,
    export_payload: DegExportPayload,
    handoff_payload: DegHandoffPayload,
    bundle_filename: str
) -> ComparisonRecord:
    """
    Build a ComparisonRecord from existing typed DEG artifacts.
    """
    # Validation: use handoff's identity as source of truth for ID
    comp_id = handoff_payload.identity.comparison_id
    if not comp_id:
        raise ValueError("comparison_id is missing in handoff_payload")
    if not bundle_filename:
        raise ValueError("bundle_filename is missing")

    return ComparisonRecord(
        comparison_id=comp_id,
        comparison_label=context.comparison_label,
        export_payload=export_payload,
        handoff_payload=handoff_payload,
        bundle_filename=bundle_filename,
        summary_metrics=context.summary_metrics
    )

def build_empty_comparison_portfolio_context(portfolio_id: Optional[str] = None) -> ComparisonPortfolioContext:
    """
    Initialize an empty portfolio context.
    """
    if portfolio_id is None:
        portfolio_id = str(uuid.uuid4())
    return ComparisonPortfolioContext(portfolio_id=portfolio_id)

def upsert_comparison_record(
    portfolio: ComparisonPortfolioContext, 
    record: ComparisonRecord
) -> ComparisonPortfolioContext:
    """
    Inserts a new record into the portfolio, or replaces an existing one if the ID matches.
    Maintaining order if replaced.
    """
    target_id = record.comparison_id
    new_records = list(portfolio.records)
    
    # Check for existing
    existing_idx = None
    for i, r in enumerate(new_records):
        if r.comparison_id == target_id:
            existing_idx = i
            break
            
    if existing_idx is not None:
        new_records[existing_idx] = record
    else:
        new_records.append(record)
        
    return ComparisonPortfolioContext(
        portfolio_id=portfolio.portfolio_id,
        records=tuple(new_records)
    )

def get_comparison_record(portfolio: ComparisonPortfolioContext, comparison_id: str) -> Optional[ComparisonRecord]:
    """
    Find a record by ID.
    """
    for r in portfolio.records:
        if r.comparison_id == comparison_id:
            return r
    return None

def list_comparison_records(portfolio: ComparisonPortfolioContext) -> List[ComparisonRecord]:
    """
    List all records in the portfolio.
    """
    return list(portfolio.records)
