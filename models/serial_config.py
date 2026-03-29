from __future__ import annotations

from dataclasses import asdict, dataclass

from models.enums import FlowControl


@dataclass
class SerialConfig:
    port: str = ""
    baud_rate: int = 115200
    data_bits: int = 8
    parity: str = "N"
    stop_bits: float = 1.0
    flow_control: FlowControl = FlowControl.NONE

    def to_dict(self) -> dict:
        data = asdict(self)
        data["flow_control"] = self.flow_control.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SerialConfig":
        return cls(
            port=data.get("port", ""),
            baud_rate=int(data.get("baud_rate", 115200)),
            data_bits=int(data.get("data_bits", 8)),
            parity=data.get("parity", "N"),
            stop_bits=float(data.get("stop_bits", 1)),
            flow_control=FlowControl(data.get("flow_control", FlowControl.NONE.value)),
        )

