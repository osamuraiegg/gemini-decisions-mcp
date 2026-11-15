#!/usr/bin/env python3
"""Example: Single-pass choice + noul + score safety ensemble (from typesafe-mario findings)."""

from __future__ import annotations

import asyncio
import json

from gemini_decisions_mcp import DecisionsClient, format_answer


async def decide_with_safety_guard(telemetry_state: dict) -> dict:
    """Evaluate action choice, binary safety override (noul), and danger score in one pass."""
    questions = {
        "next_action": {
            "type": "choice",
            "instructions": (
                "Choose the safest forward action based on obstacle proximity and enemy distance."
            ),
            "criteria": {
                "proceed": "Move forward along the ground when the path ahead is completely clear.",
                "jump": "Execute an immediate jump to clear an obstacle or hazard ahead.",
                "halt": "Stop and hold position.",
            },
        },
        "jump_needed": {
            "type": "noul",
            "instructions": (
                "Do upcoming obstacles or hazards indicate that a jump or evasive maneuver must start now?"
            ),
        },
        "danger": {
            "type": "score",
            "instructions": "Assess immediate collision danger.",
            "criteria": [
                "Safe open path",
                "Approaching obstacle or hazard",
                "Immediate collision threat",
            ],
        },
    }

    client = DecisionsClient()
    res = await client.create_decision(
        input_data=json.dumps(telemetry_state, ensure_ascii=False),
        questions=questions,
    )

    choice_ans = format_answer("choice", res.answers["next_action"])
    jump_ans = format_answer("noul", res.answers["jump_needed"])
    danger_ans = format_answer("score", res.answers["danger"])

    selected = choice_ans["choice"]
    overridden = False

    # Ensemble Safety Guard: if binary jump_needed > 0.5 or danger >= 1.0,
    # override passive forward movement with evasive jump.
    if (jump_ans["probability"] > 0.5 or danger_ans["score"] >= 1.0) and selected == "proceed":
        selected = "jump"
        overridden = True

    return {
        "final_action": selected,
        "overridden_by_safety_guard": overridden,
        "raw_choice": choice_ans,
        "jump_needed": jump_ans,
        "danger": danger_ans,
    }


async def main() -> None:
    sample_telemetry = {
        "agent": {"x": 412, "y": 79, "grounded": True, "vx": 1.8},
        "hazard": {"type": "enemy", "distance_px": 42, "approaching": True},
        "terrain": {"pipe_ahead_px": 96, "gap_ahead": False},
    }
    decision = await decide_with_safety_guard(sample_telemetry)
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
