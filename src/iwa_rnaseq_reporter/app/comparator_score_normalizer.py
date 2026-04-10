from typing import Optional
from .comparator_engine import ComparatorScoreSpec
from .comparator_ranking_input import ComparatorNormalizedScoreSpec

def normalize_overlap_score(count: int, overlap_cap: int = 500) -> float:
    """
    Scale absolute overlap count into [0.0, 1.0].
    """
    if overlap_cap <= 0:
        return 0.0
    return min(float(count) / overlap_cap, 1.0)

def normalize_top_n_overlap_score(count: int, top_n: int = 100) -> float:
    """
    Scale Top-N overlap count into [0.0, 1.0].
    """
    if top_n <= 0:
        return 0.0
    return min(float(count) / top_n, 1.0)

def normalize_correlation_score(corr: Optional[float]) -> Optional[float]:
    """
    Map correlation from [-1.0, 1.0] to [0.0, 1.0].
    Preserves None for missing values.
    """
    if corr is None:
        return None
    # Map [-1, 1] -> [0, 1]
    return (corr + 1.0) / 2.0

def build_normalized_score(
    raw_score: ComparatorScoreSpec,
    top_n: int = 100,
    overlap_cap: int = 500
) -> ComparatorNormalizedScoreSpec:
    """
    Compute all normalized indicators from a raw score spec.
    """
    return ComparatorNormalizedScoreSpec(
        overlap_score=normalize_overlap_score(raw_score.n_overlap_features, overlap_cap),
        top_n_overlap_score=normalize_top_n_overlap_score(raw_score.n_top_n_overlap_features, top_n),
        concordance_score=raw_score.direction_concordance,
        correlation_score=normalize_correlation_score(raw_score.signed_effect_correlation)
    )
