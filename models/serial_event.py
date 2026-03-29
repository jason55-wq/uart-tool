from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SerialEvent:
    direction: str
    payload: bytes
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def byte_count(self) -> int:
        return len(self.payload)

