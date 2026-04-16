from __future__ import annotations

from models.enums import SendMode


def encode_payload(payload: str, mode: SendMode) -> bytes:
    text = payload
    if mode == SendMode.ASCII:
        return text.encode("ascii", errors="replace")

    normalized = text.replace("\n", " ").replace("\r", " ").strip()
    if not normalized:
        return b""
    try:
        return bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError("HEX mode expects space-separated hexadecimal bytes.") from exc


def bytes_to_ascii(payload: bytes) -> str:
    return payload.decode("ascii", errors="replace")


def bytes_to_utf8(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


def bytes_to_hex(payload: bytes) -> str:
    return payload.hex(" ").upper()
