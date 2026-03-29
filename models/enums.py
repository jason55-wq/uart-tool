from __future__ import annotations

from enum import Enum


class ConnectionState(str, Enum):
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    ERROR = "Error"


class DisplayMode(str, Enum):
    ASCII = "ASCII"
    HEX = "HEX"
    UTF8 = "UTF-8"


class SendMode(str, Enum):
    ASCII = "ASCII"
    HEX = "HEX"


class FlowControl(str, Enum):
    NONE = "None"
    RTS_CTS = "RTS/CTS"
    XON_XOFF = "XON/XOFF"
