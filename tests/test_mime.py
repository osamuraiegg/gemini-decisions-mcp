"""Unit tests for strict MIME dispatching and input normalization."""

from __future__ import annotations

from pathlib import Path

import pytest
from google.genai._gaos.types.interactions import (
    audiocontent,
    documentcontent,
    imagecontent,
    textcontent,
    videocontent,
)
from mcp.server.mcpserver.exceptions import ToolError

from gemini_decisions_mcp.mime import STRICT_MIME_REGISTRY, normalize_input, normalize_input_item


def test_strict_mime_office_and_media_files(tmp_path: Path) -> None:
    xlsx = tmp_path / "report.xlsx"
    xlsx.write_bytes(b"PK\x03\x04dummy")
    doc_item = normalize_input_item(str(xlsx))
    assert isinstance(doc_item, documentcontent.DocumentContent)
    assert doc_item.mime_type == STRICT_MIME_REGISTRY[".xlsx"]

    docx = tmp_path / "spec.docx"
    docx.write_bytes(b"PK\x03\x04dummy")
    docx_item = normalize_input_item(docx)
    assert isinstance(docx_item, documentcontent.DocumentContent)
    assert docx_item.mime_type == STRICT_MIME_REGISTRY[".docx"]

    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"PK\x03\x04dummy")
    pptx_item = normalize_input_item(pptx)
    assert isinstance(pptx_item, documentcontent.DocumentContent)
    assert pptx_item.mime_type == STRICT_MIME_REGISTRY[".pptx"]

    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pdf_item = normalize_input_item(pdf)
    assert isinstance(pdf_item, documentcontent.DocumentContent)
    assert pdf_item.mime_type == "application/pdf"

    png = tmp_path / "screen.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    img_item = normalize_input_item(png)
    assert isinstance(img_item, imagecontent.ImageContent)
    assert img_item.mime_type == "image/png"

    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF")
    audio_item = normalize_input_item(wav)
    assert isinstance(audio_item, audiocontent.AudioContent)
    assert audio_item.mime_type == "audio/wav"

    mp4 = tmp_path / "demo.mp4"
    mp4.write_bytes(b"ftyp")
    video_item = normalize_input_item(mp4)
    assert isinstance(video_item, videocontent.VideoContent)
    assert video_item.mime_type == "video/mp4"


def test_text_file_and_raw_string(tmp_path: Path) -> None:
    py_file = tmp_path / "app.py"
    py_file.write_text("TIMEOUT = 15\n", encoding="utf-8")

    file_item = normalize_input_item(str(py_file))
    assert isinstance(file_item, textcontent.TextContent)
    assert file_item.text == "TIMEOUT = 15\n"

    raw_item = normalize_input_item("plain text state")
    assert isinstance(raw_item, textcontent.TextContent)
    assert raw_item.text == "plain text state"


def test_unknown_binary_extension_is_rejected(tmp_path: Path) -> None:
    unknown = tmp_path / "archive.bin"
    unknown.write_bytes(b"\x00\x01\x02")
    with pytest.raises(ToolError, match="Unsupported file extension"):
        normalize_input_item(unknown)


def test_dict_media_with_missing_mime_raises(tmp_path: Path) -> None:
    unknown = tmp_path / "blob.xyz"
    unknown.write_bytes(b"\x00\x01")
    with pytest.raises(ToolError, match="Missing or unknown MIME type"):
        normalize_input_item({"type": "document", "data": str(unknown)})


def test_normalize_input_list(tmp_path: Path) -> None:
    md_file = tmp_path / "spec.md"
    md_file.write_text("# Spec", encoding="utf-8")
    items = normalize_input(["Header", md_file, {"key": "value"}])
    assert len(items) == 3
    assert all(isinstance(elem, textcontent.TextContent) for elem in items)
