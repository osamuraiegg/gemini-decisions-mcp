#!/usr/bin/env python3
"""Example: Direct Excel (.xlsx) audit using STRICT_MIME_REGISTRY."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from gemini_decisions_mcp import DecisionsClient, format_answer, normalize_input


def create_dummy_workbook(xlsx_path: Path) -> None:
    """Generate a synthetic customer health spreadsheet (zero real/PII data)."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise SystemExit(
            "openpyxl is required for this example. Run with:\n"
            "  uv run --extra examples python examples/02_excel_audit.py"
        ) from exc

    wb = Workbook()
    ws = wb.active
    ws.title = "CustomerHealth"
    ws.append(["account_id", "plan", "monthly_active_days", "open_critical_tickets", "nps_score", "renewal_days"])
    ws.append(["ACCT-001", "Pro", 24, 0, 9, 120])
    ws.append(["ACCT-002", "Enterprise", 2, 4, 2, 14])
    ws.append(["ACCT-003", "Pro", 19, 1, 8, 90])
    ws.append(["ACCT-004", "Enterprise", 1, 5, 1, 7])
    wb.save(xlsx_path)


async def main() -> None:
    client = DecisionsClient()

    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = Path(tmpdir) / "synthetic_customer_health.xlsx"
        create_dummy_workbook(xlsx_path)

        # normalize_input assigns strict MIME:
        # application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
        multimodal_input = normalize_input(str(xlsx_path))

        questions = {
            "has_churn_risk": {
                "type": "noul",
                "instructions": (
                    "Are there any Enterprise accounts in this spreadsheet showing high immediate "
                    "churn risk (low monthly active days, multiple critical tickets, low NPS, "
                    "and imminent renewal)?"
                ),
            },
            "escalation_level": {
                "type": "score",
                "instructions": "Rate the urgency of customer success intervention.",
                "criteria": [
                    "Healthy - routine check-in only",
                    "Watchlist - monitor usage",
                    "Urgent - immediate executive outreach required",
                ],
            },
        }

        res = await client.create_decision(input_data=multimodal_input, questions=questions)
        formatted = {
            q_id: format_answer(q_cfg["type"], res.answers[q_id])
            for q_id, q_cfg in questions.items()
        }
        print(json.dumps(formatted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
