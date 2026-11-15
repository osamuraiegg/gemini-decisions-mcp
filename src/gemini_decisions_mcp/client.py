"""Google Gemini Decisions API client and API key resolution."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

from google import genai
from mcp.server.mcpserver.exceptions import ToolError

logger = logging.getLogger("gemini_decisions_mcp")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO if os.environ.get("DECISION_DEBUG", "0") == "1" else logging.WARNING)


def _candidate_env_paths(env_file: Path | None = None) -> list[Path]:
    """Return candidate .env file paths in precedence order."""
    candidates: list[Path] = []
    if env_file is not None:
        candidates.append(env_file)
    custom_env = os.environ.get("GEMINI_DECISIONS_ENV_FILE")
    if custom_env:
        candidates.append(Path(custom_env).expanduser())
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path.home() / ".gemini" / "config" / ".env")
    return candidates


def _is_unset_or_placeholder(value: str | None) -> bool:
    """Return True if an env value is missing, blank, or an unexpanded template placeholder."""
    if not value:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    if (stripped.startswith("${") and stripped.endswith("}")) or stripped.startswith("$"):
        return True
    return stripped in {"your-gemini-api-key-here", "YOUR_API_KEY"}


def load_env_file(env_file: Path | None = None) -> Path | None:
    """Load GEMINI_API_KEY and related settings from the first readable .env file.

    Existing non-placeholder process environment variables always take precedence.
    Returns the path loaded, or None if no .env file was loaded.
    """
    for path in _candidate_env_paths(env_file):
        if not path.exists() or not path.is_file():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and _is_unset_or_placeholder(os.environ.get(key)):
                    os.environ[key] = val
            return path
        except OSError as exc:
            logger.warning("Could not load .env file from %s: %s", path, exc)
    return None


def resolve_api_key(
    per_call_key: str | None = None,
    default_key: str | None = None,
    env_file: Path | None = None,
) -> str:
    """Resolve Gemini API key in precedence order: per-call, default, env/.env."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if (
        _is_unset_or_placeholder(per_call_key)
        and _is_unset_or_placeholder(default_key)
        and _is_unset_or_placeholder(env_key)
    ):
        load_env_file(env_file=env_file)
        env_key = os.environ.get("GEMINI_API_KEY")

    for candidate in (per_call_key, default_key, env_key):
        if not _is_unset_or_placeholder(candidate):
            assert candidate is not None
            return candidate.strip()

    raise ToolError(
        "Missing Gemini API key. Set the GEMINI_API_KEY environment variable, "
        "add GEMINI_API_KEY=... to .env (or ~/.gemini/config/.env), or pass api_key directly."
    )


class DecisionsClient:
    """Async wrapper around the Google GenAI Decisions API (gemini-decision-1)."""

    def __init__(self, default_api_key: str | None = None) -> None:
        self.default_api_key = default_api_key
        self._clients: dict[str, genai.Client] = {}

    def get_client(self, api_key: str | None = None) -> genai.Client:
        """Return a cached GenAI v1beta client for the resolved API key (HTTP keep-alive)."""
        resolved_key = resolve_api_key(api_key, self.default_api_key)
        client = self._clients.get(resolved_key)
        if client is None:
            client = genai.Client(api_key=resolved_key, http_options={"api_version": "v1beta"})
            self._clients[resolved_key] = client
        return client

    async def create_decision(
        self,
        input_data: Any,
        questions: dict[str, Any],
        model: str = "gemini-decision-1",
        api_key: str | None = None,
    ) -> Any:
        """Execute a Decisions API evaluation via google-genai SDK."""
        client = self.get_client(api_key)

        def _call_api() -> Any:
            return client.decisions.create(
                model=model,
                input=input_data,
                questions=questions,
            )

        try:
            return await asyncio.to_thread(_call_api)
        except Exception as exc:
            logger.error("Decisions API request failed: %s", exc)
            raise ToolError(f"Gemini Decisions API error: {exc}") from exc
