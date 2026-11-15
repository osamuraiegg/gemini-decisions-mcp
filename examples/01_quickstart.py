#!/usr/bin/env python3
"""Quickstart example: noul, choice, score, and evaluate with gemini-decision-1."""

from __future__ import annotations

import asyncio
import json
import time

from gemini_decisions_mcp import DecisionsClient, format_answer


async def main() -> None:
    client = DecisionsClient()

    sample_log = """
    [2026-11-15T09:12:03Z] ERROR checkout-service: psycopg.errors.DeadlockDetected:
    deadlock detected while updating table "inventory_locks" (PID 4821)
    DETAIL: Process 4821 waits for ShareLock on transaction 99124; blocked by process 4819.
    """

    questions = {
        "is_db_issue": {
            "type": "noul",
            "instructions": "Is this failure caused by a database locking or concurrency issue?",
        },
        "root_cause": {
            "type": "choice",
            "instructions": "Classify the primary failure domain for incident routing.",
            "criteria": {
                "database": "Database deadlock, lock contention, query failure, or connection pool exhaustion.",
                "network": "DNS resolution failure, TLS handshake error, or TCP timeout.",
                "auth": "Expired token, invalid signature, or permission denied.",
                "ui": "Frontend rendering or client-side validation error.",
            },
        },
        "severity": {
            "type": "score",
            "instructions": "Rate the operational severity of this production log.",
            "criteria": [
                "Low - informational or self-healing",
                "Medium - localized retryable failure",
                "High - user-facing checkout impact",
                "Critical - full outage or data corruption",
            ],
        },
    }

    started = time.perf_counter()
    res = await client.create_decision(input_data=sample_log, questions=questions)
    latency_ms = (time.perf_counter() - started) * 1000

    formatted = {
        q_id: format_answer(q_cfg["type"], res.answers[q_id])
        for q_id, q_cfg in questions.items()
    }
    print(f"Latency: {latency_ms:.1f} ms | Output tokens: 0")
    print(json.dumps(formatted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
