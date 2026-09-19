"""Rejection of unsupported binary requirement uploads (#13)."""
import pytest

from extract import UnsupportedDocumentError, extract_text


def test_markdown_and_plain_text_still_decode():
    assert extract_text("notes.md", b"# Title\nhello") == "# Title\nhello"
    assert extract_text("notes.txt", "café".encode("utf-8")) == "café"


def test_xlsx_magic_bytes_are_rejected():
    payload = b"PK\x03\x04" + b"\x00" * 32
    with pytest.raises(UnsupportedDocumentError) as ei:
        extract_text("sheet.xlsx", payload)
    msg = str(ei.value)
    assert "Supported formats" in msg
    assert "xlsx" in msg.lower() or "ZIP" in msg or "Open XML" in msg


def test_legacy_ole_doc_is_rejected():
    payload = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16
    with pytest.raises(UnsupportedDocumentError) as ei:
        extract_text("spec.doc", payload)
    assert "Supported formats" in str(ei.value)
    assert "OLE" in str(ei.value) or "doc" in str(ei.value)


def test_random_binary_is_rejected_with_supported_formats():
    payload = bytes(range(256))
    with pytest.raises(UnsupportedDocumentError) as ei:
        extract_text("blob.bin", payload)
    assert "Supported formats: PDF, DOCX, Markdown, and plain text" in str(ei.value)
