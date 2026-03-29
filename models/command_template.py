from __future__ import annotations

from dataclasses import asdict, dataclass, field
from uuid import uuid4

from models.enums import SendMode


@dataclass
class CommandTemplate:
    name: str
    payload: str
    mode: SendMode = SendMode.ASCII
    category: str = "General"
    template_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["mode"] = self.mode.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "CommandTemplate":
        return cls(
            name=data["name"],
            payload=data["payload"],
            mode=SendMode(data.get("mode", SendMode.ASCII.value)),
            category=data.get("category", "General"),
            template_id=data.get("template_id", str(uuid4())),
        )

