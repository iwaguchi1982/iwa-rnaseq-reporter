import pytest
import pandas as pd
from typing import Tuple
from iwa_rnaseq_reporter.app.comparator_review_session import (
    ComparatorReviewRowSpec,
    ComparatorReviewSessionContext
)
from iwa_rnaseq_reporter.app.comparator_review_table import ComparatorReviewFilterSpec
from iwa_rnaseq_reporter.app.comparator_review_table_builder import (
    build_comparator_review_table_context,
    build_comparator_review_table_dataframe
)

@pytest.fixture
def mock_session_ctx():
    rows = (
        ComparatorReviewRowSpec(
            comparison_id="C1", decision_status="consensus", decided_label_key="L1", 
            decided_label_display="Label 1", support_margin=0.2, has_conflict=False, 
            has_weak_support=False, reason_codes=("code1",), search_text="c1 consensus label 1 code1"
        ),
        ComparatorReviewRowSpec(
            comparison_id="C2", decision_status="no_consensus", decided_label_key=None, 
            support_margin=0.01, has_conflict=True, has_weak_support=True, 
            reason_codes=("code2",), search_text="c2 no_consensus code2"
        ),
        ComparatorReviewRowSpec(
            comparison_id="C3", decision_status="insufficient_evidence", decided_label_key="L2", 
            support_margin=None, has_conflict=False, has_weak_support=True, 
            reason_codes=("code3",), search_text="c3 insufficient_evidence label 2 code3"
        )
    )
    from unittest.mock import MagicMock
    ctx = MagicMock(spec=ComparatorReviewSessionContext)
    ctx.rows = rows
    return ctx

def test_build_review_table_no_filter(mock_session_ctx):
    """Verify that empty filter returns all rows in order."""
    filters = ComparatorReviewFilterSpec()
    ctx = build_comparator_review_table_context(mock_session_ctx, filters)
    
    assert len(ctx.filtered_rows) == 3
    assert ctx.summary.n_total_rows == 3
    assert ctx.summary.n_filtered_rows == 3
    assert ctx.filtered_rows[0].comparison_id == "C1"

def test_filter_by_decision_status(mock_session_ctx):
    filters = ComparatorReviewFilterSpec(decision_statuses=("consensus", "no_consensus"))
    ctx = build_comparator_review_table_context(mock_session_ctx, filters)
    
    assert len(ctx.filtered_rows) == 2
    assert all(r.decision_status in ("consensus", "no_consensus") for r in ctx.filtered_rows)

def test_filter_by_decided_label(mock_session_ctx):
    filters = ComparatorReviewFilterSpec(decided_label_keys=("L2",))
    ctx = build_comparator_review_table_context(mock_session_ctx, filters)
    
    assert len(ctx.filtered_rows) == 1
    assert ctx.filtered_rows[0].comparison_id == "C3"

def test_filter_by_conflict_mode(mock_session_ctx):
    # conflict_only
    ctx_c = build_comparator_review_table_context(mock_session_ctx, ComparatorReviewFilterSpec(conflict_mode="conflict_only"))
    assert len(ctx_c.filtered_rows) == 1
    assert ctx_c.filtered_rows[0].comparison_id == "C2"
    
    # no_conflict_only
    ctx_nc = build_comparator_review_table_context(mock_session_ctx, ComparatorReviewFilterSpec(conflict_mode="no_conflict_only"))
    assert len(ctx_nc.filtered_rows) == 2
    assert "C1" in [r.comparison_id for r in ctx_nc.filtered_rows]

def test_filter_by_weak_support_mode(mock_session_ctx):
    ctx_w = build_comparator_review_table_context(mock_session_ctx, ComparatorReviewFilterSpec(weak_support_mode="weak_only"))
    assert len(ctx_w.filtered_rows) == 2
    assert set(r.comparison_id for r in ctx_w.filtered_rows) == {"C2", "C3"}

def test_filter_by_search_query(mock_session_ctx):
    ctx_q = build_comparator_review_table_context(mock_session_ctx, ComparatorReviewFilterSpec(search_query="code3"))
    assert len(ctx_q.filtered_rows) == 1
    assert ctx_q.filtered_rows[0].comparison_id == "C3"

def test_combined_filters(mock_session_ctx):
    filters = ComparatorReviewFilterSpec(
        decision_statuses=("no_consensus", "insufficient_evidence"),
        weak_support_mode="weak_only",
        search_query="c2"
    )
    ctx = build_comparator_review_table_context(mock_session_ctx, filters)
    assert len(ctx.filtered_rows) == 1
    assert ctx.filtered_rows[0].comparison_id == "C2"

def test_filtered_summary_counts(mock_session_ctx):
    filters = ComparatorReviewFilterSpec(weak_support_mode="weak_only")
    ctx = build_comparator_review_table_context(mock_session_ctx, filters)
    
    assert ctx.summary.n_filtered_rows == 2
    assert ctx.summary.n_no_consensus == 1
    assert ctx.summary.n_insufficient_evidence == 1
    assert ctx.summary.n_consensus == 0
    assert ctx.summary.decision_status_counts["no_consensus"] == 1
    assert ctx.summary.decided_label_counts == {"L2": 1}

def test_dataframe_formatting(mock_session_ctx):
    df = build_comparator_review_table_dataframe(mock_session_ctx.rows)
    
    assert len(df) == 3
    # Check fallback for label
    assert df.loc[df["comparison_id"] == "C1", "decided_label"].values[0] == "Label 1"
    assert df.loc[df["comparison_id"] == "C2", "decided_label"].values[0] == "-"
    
    # Check margin formatting
    assert df.loc[df["comparison_id"] == "C3", "support_margin"].values[0] == "-"
    
    # Check list join for reason_codes
    assert df.loc[df["comparison_id"] == "C1", "reason_codes"].values[0] == "code1"
