"""Extraction de texte, sans dépendance : .txt/.md/.csv/.eml/.html, PDF, DOCX.

Le PDF est lu via sa couche texte (décompression des streams puis opérateurs
``Tj``/``TJ``). Un PDF scanné n'a pas de couche texte : l'extraction lève alors
une erreur explicite plutôt que de renvoyer du vide, et l'agent doit le dire.
"""

from __future__ import annotations

import io
import re
import zipfile
import zlib
from html import unescape
from pathlib import Path

SUPPORTED = {".txt", ".md", ".csv", ".json", ".eml", ".html", ".htm", ".log", ".pdf", ".docx"}

_PDF_TOKEN = re.compile(rb"\((?:[^()\\]|\\.)*\)\s*Tj|\[(?:[^\]]|\\.)*\]\s*TJ|T\*|TD|Td")
_PDF_LITERAL = re.compile(rb"\((?:[^()\\]|\\.)*\)")


class ExtractionError(Exception):
    pass


def extraire_texte(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ExtractionError(f"format non pris en charge : {suffix or 'sans extension'}")
    data = path.read_bytes()
    if suffix == ".pdf":
        return pdf_text(data)
    if suffix == ".docx":
        return docx_text(data)
    if suffix in {".html", ".htm"}:
        return html_text(data.decode("utf-8", "replace"))
    if suffix == ".eml":
        return email_text(data)
    return data.decode("utf-8", "replace")


def html_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", markup)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", markup)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]{2,}", " ", unescape(text)).strip()


def email_text(data: bytes) -> str:
    raw = data.decode("utf-8", "replace")
    headers, _, body = raw.partition("\n\n")
    return headers.strip() + "\n\n" + re.sub(r"\n{3,}", "\n\n", body.strip())


def pdf_text(data: bytes) -> str:
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = match.group(1)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        text = _pdf_stream_text(raw)
        if text.strip():
            chunks.append(text)
    text = "\n".join(chunks)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ExtractionError("PDF sans couche texte (scan ?) — OCR nécessaire avant ingestion")
    return text


def _pdf_stream_text(stream: bytes) -> str:
    out: list[str] = []
    for token in _PDF_TOKEN.finditer(stream):
        value = token.group(0)
        if value.startswith(b"("):
            literal = _PDF_LITERAL.match(value)
            if literal:
                out.append(_pdf_literal(literal.group(0)))
        elif value.startswith(b"["):
            out.append("".join(_pdf_literal(lit.group(0)) for lit in _PDF_LITERAL.finditer(value)))
        else:
            out.append("\n")
    return "".join(out)


def _pdf_literal(token: bytes) -> str:
    body = token[1:-1]
    body = re.sub(rb"\\([nrtbf])", lambda m: {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"", b"f": b""}[m.group(1)], body)
    body = re.sub(rb"\\([()\\])", rb"\1", body)
    body = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8) & 0xFF]), body)
    return body.decode("cp1252", "replace")


def docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", "replace")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ExtractionError(f"DOCX illisible : {exc}") from exc
    xml = xml.replace("</w:p>", "\n").replace("<w:br/>", "\n").replace("<w:br />", "\n")
    xml = xml.replace("<w:tab/>", "\t").replace("<w:tab />", "\t")
    text = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"\n{3,}", "\n\n", unescape(text)).strip()
