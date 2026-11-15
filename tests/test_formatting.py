"""Unit tests for Decisions API answer formatting."""

from __future__ import annotations

from types import SimpleNamespace

from gemini_decisions_mcp.formatting import (
    format_answer,
    format_choice_answer,
    format_noul_answer,
    format_score_answer,
)


def test_format_noul_answer_from_object_and_dict() -> None:
    obj_ans = SimpleNamespace(probability=0.87, confidence=0.87)
    assert format_noul_answer(obj_ans) == {
        "probability": 0.87,
        "is_likely": True,
        "confidence": 0.87,
    }

    dict_ans = {"noul": 0.12}
    res = format_noul_answer(dict_ans)
    assert res["probability"] == 0.12
    assert res["is_likely"] is False
    assert abs(res["confidence"] - 0.88) < 1e-9


def test_format_choice_answer() -> None:
    ans = SimpleNamespace(
        value="database",
        probabilities={"database": 0.91, "network": 0.09},
        confidence=0.91,
    )
    assert format_choice_answer(ans) == {
        "choice": "database",
        "probabilities": {"database": 0.91, "network": 0.09},
        "confidence": 0.91,
    }


def test_format_score_answer() -> None:
    ans = SimpleNamespace(
        score=2.45,
        confidence=0.78,
        legend={"0": "Low", "1": "Med", "2": "High", "3": "Critical"},
        probabilities={"2": 0.55, "3": 0.45},
    )
    assert format_score_answer(ans) == {
        "score": 2.45,
        "confidence": 0.78,
        "legend": {"0": "Low", "1": "Med", "2": "High", "3": "Critical"},
        "probabilities": {"2": 0.55, "3": 0.45},
    }


def test_format_answer_fallback() -> None:
    assert format_answer("custom", {"raw_val": 42}) == {
        "type": "custom",
        "raw": {"raw_val": 42},
    }
