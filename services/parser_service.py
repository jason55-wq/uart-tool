from __future__ import annotations

from abc import ABC, abstractmethod

from models.enums import DisplayMode
from models.serial_event import SerialEvent
from utils.encoding import bytes_to_ascii, bytes_to_hex, bytes_to_utf8


class BaseParser(ABC):
    """Extension point for future protocol and display parsers."""

    @abstractmethod
    def render(self, event: SerialEvent, options: dict) -> str:
        raise NotImplementedError


class PlainTextParser(BaseParser):
    def render(self, event: SerialEvent, options: dict) -> str:
        return _compose_line(bytes_to_ascii(event.payload), event, options)


class HexParser(BaseParser):
    def render(self, event: SerialEvent, options: dict) -> str:
        return _compose_line(bytes_to_hex(event.payload), event, options)


class Utf8Parser(BaseParser):
    def render(self, event: SerialEvent, options: dict) -> str:
        return _compose_line(bytes_to_utf8(event.payload), event, options)


class ParserRegistry:
    """Registry that can later load parser plugins dynamically."""

    def __init__(self) -> None:
        self._parsers = {
            DisplayMode.ASCII: PlainTextParser(),
            DisplayMode.HEX: HexParser(),
            DisplayMode.UTF8: Utf8Parser(),
        }

    def get_parser(self, mode: DisplayMode) -> BaseParser:
        return self._parsers[mode]


def _compose_line(content: str, event: SerialEvent, options: dict) -> str:
    parts: list[str] = []
    if options.get("show_timestamp", True):
        parts.append(event.timestamp.strftime("%H:%M:%S.%f")[:-3])
    if options.get("show_direction", True):
        parts.append(event.direction)
    parts.append(content)
    line = " | ".join(parts)
    newline = options.get("newline", "\\n")
    return line + _newline_token(newline)


def _newline_token(mode: str) -> str:
    mapping = {
        "\\n": "\n",
        "\\r\\n": "\r\n",
        "none": "",
    }
    return mapping.get(mode, "\n")
