"""Vector math and cosine similarity utilities for semantic embeddings."""

from __future__ import annotations

import math


def normalize_vector(vector: list[float]) -> list[float]:
    """Normalizes a float vector to unit length (L2 norm = 1.0)."""
    norm_sq = sum(x * x for x in vector)
    if norm_sq <= 1e-12:
        return [0.0] * len(vector)
    inv_norm = 1.0 / math.sqrt(norm_sq)
    return [x * inv_norm for x in vector]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two float vectors.

    Returns a score between -1.0 and 1.0. For unit-normalized vectors,
    this is equivalent to the dot product.
    """
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b, strict=False):
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0

    sim = dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
    # Clamp to [-1.0, 1.0] to handle floating point imprecision
    return max(-1.0, min(1.0, sim))


def rank_by_similarity(
    query_vector: list[float],
    candidate_vectors: list[list[float]],
    threshold: float = 0.0,
) -> list[tuple[int, float]]:
    """Ranks candidate vectors by cosine similarity to query_vector.

    Returns a list of (candidate_index, similarity_score) sorted descending by score.
    Filters out candidates with score < threshold.
    """
    scored = []
    for idx, cand in enumerate(candidate_vectors):
        score = cosine_similarity(query_vector, cand)
        if score >= threshold:
            scored.append((idx, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
