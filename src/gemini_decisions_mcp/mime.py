"""Strict multimodal MIME dispatching and input normalization for Gemini Decisions API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.genai._gaos.types.interactions import (
    audiocontent,
    documentcontent,
    imagecontent,
    textcontent,
    videocontent,
)
from mcp.server.mcpserver.exceptions import ToolError

# Strict MIME registry matching Google GenAI specifications exactly.
# Ambiguous MIME types like application/octet-stream or wrong Office MIME types
# can cause silent model degradation or off-target answers without raising errors.
STRICT_MIME_REGISTRY: dict[str, str] = {
    # Spreadsheets & Data
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    # Documents
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".dotx": "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    ".odt": "application/vnd.oasis.opendocument.text",
    # Presentations
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/ms-powerpoint",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    # Audio
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/m4a",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    # Video
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/mov",
    ".avi": "video/avi",
    ".wmv": "video/wmv",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpg",
    ".3gp": "video/3gpp",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".tsv",
    ".yaml",
    ".yml",
    ".toml",
    ".ts",
    ".js",
    ".py",
    ".rs",
    ".go",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".sh",
    ".bash",
    ".zsh",
    ".html",
    ".css",
    ".xml",
    ".sql",
}

_CONTENT_CLASS_BY_TYPE = {
    "document": documentcontent.DocumentContent,
    "image": imagecontent.ImageContent,
    "audio": audiocontent.AudioContent,
    "video": videocontent.VideoContent,
}


def _build_media_content(path: Path, mime: str) -> Any:
    """Instantiate the GenAI content class corresponding to a strict MIME type."""
    if mime.startswith("image/"):
        return imagecontent.ImageContent(data=path, mime_type=mime)
    if mime.startswith("audio/"):
        return audiocontent.AudioContent(data=path, mime_type=mime)
    if mime.startswith("video/"):
        return videocontent.VideoContent(data=path, mime_type=mime)
    return documentcontent.DocumentContent(data=path, mime_type=mime)


def normalize_input_item(item: Any) -> Any:
    """Normalize a single input item into a multimodal GenAI content object."""
    if isinstance(item, (str, Path)):
        path = Path(item)
        if path.exists() and path.is_file():
            ext = path.suffix.lower()
            if ext in STRICT_MIME_REGISTRY:
                return _build_media_content(path, STRICT_MIME_REGISTRY[ext])
            if ext in TEXT_EXTENSIONS:
                try:
                    return textcontent.TextContent(
                        text=path.read_text(encoding="utf-8", errors="replace")
                    )
                except Exception as exc:
                    raise ToolError(f"Failed to read text file '{path}': {exc}") from exc
            raise ToolError(
                f"Unsupported file extension '{ext}' for file '{path}'. "
                "To prevent misclassification, unknown binary files cannot be sent as "
                "application/octet-stream. Please convert to one of: "
                f"{sorted(STRICT_MIME_REGISTRY.keys())}"
            )
        return textcontent.TextContent(text=str(item))

    if isinstance(item, dict):
        item_type = item.get("type")
        if item_type in _CONTENT_CLASS_BY_TYPE:
            data = item.get("data")
            mime = item.get("mime_type")
            if isinstance(data, (str, Path)) and Path(data).exists() and Path(data).is_file():
                path = Path(data)
                mime = mime or STRICT_MIME_REGISTRY.get(path.suffix.lower())
                if not mime:
                    raise ToolError(
                        f"Missing or unknown MIME type for '{path}'. "
                        "Provide 'mime_type' explicitly or use a supported extension."
                    )
                return _CONTENT_CLASS_BY_TYPE[item_type](data=path, mime_type=mime)
            return item
        if item_type == "text" and "text" in item:
            return item
        return textcontent.TextContent(text=json.dumps(item, ensure_ascii=False, indent=2))

    return textcontent.TextContent(text=str(item))


def normalize_input(state: str | dict[str, Any] | list[Any]) -> Any:
    """Normalize input state (single item or list) for Decisions API input."""
    if isinstance(state, list):
        return [normalize_input_item(elem) for elem in state]
    return normalize_input_item(state)
