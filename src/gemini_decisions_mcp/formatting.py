"""Response formatting utilities for Gemini Decisions API answers."""

from __future__ import annotations

from typing import Any


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Safely read a field from either a dict or an SDK object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def format_noul_answer(answer: Any) -> dict[str, Any]:
    """Format a binary (noul) decision answer."""
    prob = float(get_field(answer, "probability", get_field(answer, "noul", 0.0)))
    conf = float(get_field(answer, "confidence", prob if prob >= 0.5 else 1.0 - prob))
    return {
        "probability": prob,
        "is_likely": prob >= 0.5,
        "confidence": conf,
    }


def format_choice_answer(answer: Any) -> dict[str, Any]:
    """Format a categorical (choice) decision answer."""
    choice_val = get_field(answer, "value", get_field(answer, "choice"))
    probs = get_field(answer, "probabilities", {})
    conf = float(get_field(answer, "confidence", 0.0))
    return {
        "choice": choice_val,
        "probabilities": dict(probs) if probs else {},
        "confidence": conf,
    }


def format_score_answer(answer: Any) -> dict[str, Any]:
    """Format a rubric-based (score) decision answer."""
    score_val = float(get_field(answer, "score", 0.0))
    probs = get_field(answer, "probabilities", {})
    legend = get_field(answer, "legend", {})
    conf = float(get_field(answer, "confidence", 0.0))
    return {
        "score": score_val,
        "confidence": conf,
        "legend": dict(legend) if legend else {},
        "probabilities": dict(probs) if probs else {},
    }


def format_answer(q_type: str, answer: Any) -> dict[str, Any]:
    """Dispatch formatting according to question primitive type."""
    if q_type == "noul":
        return format_noul_answer(answer)
    if q_type == "choice":
        return format_choice_answer(answer)
    if q_type == "score":
        return format_score_answer(answer)
    return {
        "type": q_type,
        "raw": answer if isinstance(answer, (dict, list, str, int, float, bool)) else str(answer),
    }
