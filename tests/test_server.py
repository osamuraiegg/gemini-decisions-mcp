"""Unit tests for API key resolution and MCP server tool registration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from gemini_decisions_mcp.client import DecisionsClient, resolve_api_key
from gemini_decisions_mcp.server import create_server


def test_resolve_api_key_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('GEMINI_API_KEY="from-dotenv"\n', encoding="utf-8")

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_DECISIONS_ENV_FILE", str(env_file))

    assert resolve_api_key(per_call_key="from-call", default_key="from-default") == "from-call"
    assert resolve_api_key(default_key="from-default") == "from-default"
    assert resolve_api_key() == "from-dotenv"

    # Unexpanded placeholder (e.g. from mcp_config.json "${GEMINI_API_KEY}") must fall back to .env
    monkeypatch.setenv("GEMINI_API_KEY", "${GEMINI_API_KEY}")
    assert resolve_api_key() == "from-dotenv"


def test_resolve_api_key_missing_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_DECISIONS_ENV_FILE", str(tmp_path / "nonexistent.env"))
    monkeypatch.chdir(tmp_path)

    with (
        patch("gemini_decisions_mcp.client.Path.home", return_value=tmp_path),
        pytest.raises(ToolError, match="Missing Gemini API key"),
    ):
        resolve_api_key()


@pytest.mark.asyncio
async def test_server_tool_registration_and_alias_toggle() -> None:
    server_all = create_server(default_api_key="dummy-key", include_legacy_aliases=True)
    tools_all = {tool.name for tool in await server_all.list_tools()}
    assert tools_all == {
        "decision_noul",
        "decision_choice",
        "decision_score",
        "decision_evaluate",
        "jev_noul",
        "jev_choice",
        "jev_score",
        "jev_evaluate",
    }

    server_modern = create_server(default_api_key="dummy-key", include_legacy_aliases=False)
    tools_modern = {tool.name for tool in await server_modern.list_tools()}
    assert tools_modern == {
        "decision_noul",
        "decision_choice",
        "decision_score",
        "decision_evaluate",
    }


@pytest.mark.asyncio
async def test_server_tool_execution_with_mocked_client() -> None:
    mock_response = SimpleNamespace(
        answers={
            "noul": SimpleNamespace(probability=0.92, confidence=0.92),
            "q_choice": SimpleNamespace(
                value="database",
                probabilities={"database": 0.9, "network": 0.1},
                confidence=0.9,
            ),
            "q_score": SimpleNamespace(
                score=1.75,
                confidence=0.8,
                legend={"0": "Low", "1": "Med", "2": "High"},
                probabilities={"1": 0.25, "2": 0.75},
            ),
        },
        usage=SimpleNamespace(input_tokens=128),
    )

    with patch.object(DecisionsClient, "create_decision", new=AsyncMock(return_value=mock_response)):
        server = create_server(default_api_key="dummy-key")
        noul_res = await server.call_tool(
            "decision_noul",
            {
                "state": "def ok(): return True",
                "instructions": "Is this valid Python?",
            },
        )
        assert not noul_res.is_error
        payload = noul_res.structured_content
        assert payload["probability"] == 0.92
        assert payload["is_likely"] is True
        assert payload["usage"] == {"input_tokens": 128, "output_tokens": 0}
        assert isinstance(payload["latency_ms"], float)
        assert payload["latency_ms"] >= 0.0
        assert payload["model"] == "gemini-decision-1"

        eval_res = await server.call_tool(
            "jev_evaluate",
            {
                "state": "db timeout",
                "questions": {
                    "q_choice": {"type": "choice", "instructions": "Pick", "criteria": {"database": "db", "network": "net"}},
                    "q_score": {"type": "score", "instructions": "Rate", "criteria": ["Low", "Med", "High"]},
                },
            },
        )
        assert not eval_res.is_error
        eval_payload = eval_res.structured_content
        assert eval_payload["answers"]["q_choice"]["choice"] == "database"
        assert eval_payload["answers"]["q_score"]["score"] == 1.75
        assert eval_payload["latency_ms"] >= 0.0


def test_decisions_client_caches_client_per_api_key() -> None:
    with patch("gemini_decisions_mcp.client.genai.Client") as mock_client_cls:
        mock_client_cls.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        decisions_client = DecisionsClient(default_api_key="key-a")

        c1 = decisions_client.get_client()
        c2 = decisions_client.get_client()
        c3 = decisions_client.get_client(api_key="key-b")

        assert c1 is c2
        assert c1 is not c3
        assert mock_client_cls.call_count == 2
