#!/usr/bin/env python3
"""Example: Stage 1 of the 2-Stage Hybrid Specification Review (Pattern G)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from gemini_decisions_mcp import DecisionsClient, format_answer, normalize_input


async def main() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    spec_path = fixtures_dir / "sample_spec.md"
    impl_path = fixtures_dir / "sample_impl.py"

    state = normalize_input(
        [
            f"=== SPECIFICATION ({spec_path.name}) ===",
            spec_path,
            f"=== IMPLEMENTATION ({impl_path.name}) ===",
            impl_path,
        ]
    )

    questions = {
        "q_constants_match": {
            "type": "noul",
            "instructions": (
                "Do all numeric configuration constants (such as REQUEST_TIMEOUT_SECONDS, "
                "MAX_RETRIES, BACKOFF_BASE_SECONDS) match exactly between the specification and implementation?"
            ),
        },
        "q_api_signature_match": {
            "type": "noul",
            "instructions": (
                "Do all parameters and return shapes of authorize() in the implementation match "
                "what is documented in the specification without undocumented parameters?"
            ),
        },
        "q_exceptions_match": {
            "type": "noul",
            "instructions": (
                "Are all custom exception classes and validation errors raised in the implementation "
                "documented in the specification?"
            ),
        },
        "q_maturity": {
            "type": "score",
            "instructions": "Rate the specification's alignment and completeness relative to the code.",
            "criteria": [
                "Outdated or contradictory",
                "Partially aligned with gaps",
                "Accurate and review-ready",
            ],
        },
    }

    client = DecisionsClient()
    res = await client.create_decision(input_data=state, questions=questions)

    print("=== Stage 1: Objective Scan (gemini-decision-1) ===")
    for q_id, q_cfg in questions.items():
        ans = format_answer(q_cfg["type"], res.answers[q_id])
        status = ""
        if q_cfg["type"] == "noul":
            p = ans["probability"]
            status = "PASS" if p >= 0.8 else ("FAIL (Discrepancy)" if p <= 0.2 else "NEEDS_REVIEW")
        print(f"- {q_id}: {json.dumps(ans, ensure_ascii=False)} {status}")


if __name__ == "__main__":
    asyncio.run(main())
