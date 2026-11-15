"""MCP Server exposing Google Gemini Decisions API primitives."""

from __future__ import annotations

import argparse
import time
from typing import Any

from mcp.server.mcpserver import MCPServer

from .client import DecisionsClient
from .formatting import format_answer, get_field
from .mime import normalize_input


def create_server(
    default_api_key: str | None = None,
    include_legacy_aliases: bool = True,
) -> MCPServer:
    """Create and configure the Gemini Decisions MCP Server."""
    server = MCPServer(
        name="gemini-decisions",
        instructions=(
            "MCP server routing System One decision and evaluation requests to Google Gemini "
            "Decisions API (gemini-decision-1). Supports multimodal input (Excel, Word, "
            "PowerPoint, PDF, Images, Audio, Video, Text) with zero output tokens and calibrated "
            "probabilities."
        ),
    )
    decisions_client = DecisionsClient(default_api_key=default_api_key)

    async def _handle_evaluate(
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, dict[str, Any]],
        model: str = "gemini-decision-1",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        normalized_input = normalize_input(state)
        started = time.perf_counter()
        res = await decisions_client.create_decision(
            input_data=normalized_input,
            questions=questions,
            model=model,
            api_key=api_key,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)

        raw_answers = get_field(res, "answers", {})
        formatted_answers: dict[str, Any] = {}
        for q_id, q_cfg in questions.items():
            q_type = q_cfg.get("type", "unknown")
            ans_obj = (
                raw_answers.get(q_id)
                if isinstance(raw_answers, dict)
                else getattr(raw_answers, q_id, None)
            )
            formatted_answers[q_id] = format_answer(q_type, ans_obj)

        raw_usage = get_field(res, "usage", {})
        usage = {
            "input_tokens": get_field(
                raw_usage, "input_tokens", get_field(raw_usage, "total_input_tokens", 0)
            ),
            "output_tokens": 0,
        }

        return {
            "answers": formatted_answers,
            "usage": usage,
            "latency_ms": latency_ms,
            "model": model,
        }

    async def _handle_noul(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: dict[str, str] | None = None,
        model: str = "gemini-decision-1",
        question_id: str = "noul",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        q_def: dict[str, Any] = {
            "type": "noul",
            "instructions": instructions,
        }
        if criteria:
            q_def["criteria"] = criteria

        eval_res = await _handle_evaluate(
            state=state,
            questions={question_id: q_def},
            model=model,
            api_key=api_key,
        )
        answer = eval_res["answers"].get(question_id, {})
        return {
            "question_id": question_id,
            "probability": answer.get("probability", 0.0),
            "is_likely": answer.get("is_likely", False),
            "confidence": answer.get("confidence", 0.0),
            "usage": eval_res["usage"],
            "latency_ms": eval_res["latency_ms"],
            "model": model,
        }

    async def _handle_choice(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: dict[str, str | None],
        model: str = "gemini-decision-1",
        question_id: str = "choice",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        q_def = {
            "type": "choice",
            "instructions": instructions,
            "criteria": criteria,
        }
        eval_res = await _handle_evaluate(
            state=state,
            questions={question_id: q_def},
            model=model,
            api_key=api_key,
        )
        answer = eval_res["answers"].get(question_id, {})
        return {
            "question_id": question_id,
            "choice": answer.get("choice"),
            "confidence": answer.get("confidence", 0.0),
            "probabilities": answer.get("probabilities", {}),
            "usage": eval_res["usage"],
            "latency_ms": eval_res["latency_ms"],
            "model": model,
        }

    async def _handle_score(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: list[str],
        model: str = "gemini-decision-1",
        question_id: str = "score",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        q_def = {
            "type": "score",
            "instructions": instructions,
            "criteria": criteria,
        }
        eval_res = await _handle_evaluate(
            state=state,
            questions={question_id: q_def},
            model=model,
            api_key=api_key,
        )
        answer = eval_res["answers"].get(question_id, {})
        return {
            "question_id": question_id,
            "score": answer.get("score", 0.0),
            "confidence": answer.get("confidence", 0.0),
            "legend": answer.get("legend", {}),
            "probabilities": answer.get("probabilities", {}),
            "usage": eval_res["usage"],
            "latency_ms": eval_res["latency_ms"],
            "model": model,
        }

    _EVALUATE_DESC = (
        "Evaluate multimodal state (Excel, Word, PPTX, PDF, media, code, text) "
        "against multiple typed questions in parallel using Gemini Decisions API."
    )
    _NOUL_DESC = (
        "Evaluate a binary (yes/no) question against multimodal input (Excel, PDF, media, text). "
        "Returns calibrated probability (0.0 to 1.0) and confidence."
    )
    _CHOICE_DESC = (
        "Select one option from a defined set of 2 to 255 choices over multimodal input. "
        "Returns selected choice, confidence, and probability distribution."
    )
    _SCORE_DESC = (
        "Rate multimodal input along an ordered rubric of at least two descriptive levels. "
        "Returns a weighted float score and confidence."
    )

    async def decision_evaluate(
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, dict[str, Any]],
        model: str = "gemini-decision-1",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        return await _handle_evaluate(state=state, questions=questions, model=model, api_key=api_key)

    async def decision_noul(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: dict[str, str] | None = None,
        model: str = "gemini-decision-1",
        question_id: str = "noul",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        return await _handle_noul(
            state=state,
            instructions=instructions,
            criteria=criteria,
            model=model,
            question_id=question_id,
            api_key=api_key,
        )

    async def decision_choice(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: dict[str, str | None],
        model: str = "gemini-decision-1",
        question_id: str = "choice",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        return await _handle_choice(
            state=state,
            instructions=instructions,
            criteria=criteria,
            model=model,
            question_id=question_id,
            api_key=api_key,
        )

    async def decision_score(
        state: str | dict[str, Any] | list[Any],
        instructions: str | dict[str, Any] | list[Any],
        criteria: list[str],
        model: str = "gemini-decision-1",
        question_id: str = "score",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        return await _handle_score(
            state=state,
            instructions=instructions,
            criteria=criteria,
            model=model,
            question_id=question_id,
            api_key=api_key,
        )

    tool_specs = [
        ("decision_evaluate", "jev_evaluate", decision_evaluate, _EVALUATE_DESC),
        ("decision_noul", "jev_noul", decision_noul, _NOUL_DESC),
        ("decision_choice", "jev_choice", decision_choice, _CHOICE_DESC),
        ("decision_score", "jev_score", decision_score, _SCORE_DESC),
    ]

    for primary_name, legacy_name, fn, desc in tool_specs:
        server.add_tool(fn, name=primary_name, description=desc)
        if include_legacy_aliases:
            server.add_tool(fn, name=legacy_name, description=desc)

    return server


def main() -> None:
    """CLI entrypoint for Gemini Decisions MCP Server."""
    parser = argparse.ArgumentParser(description="Gemini Decisions MCP Server")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API Key (defaults to GEMINI_API_KEY env variable or .env)",
    )
    parser.add_argument(
        "--no-legacy-aliases",
        action="store_true",
        help="Register only decision_* tools without jev_* compatibility aliases.",
    )
    args = parser.parse_args()

    server = create_server(
        default_api_key=args.api_key,
        include_legacy_aliases=not args.no_legacy_aliases,
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
