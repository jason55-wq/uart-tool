from models.enums import FlowControl
from models.serial_config import SerialConfig


def test_serial_config_roundtrip() -> None:
    config = SerialConfig(
        port="COM3",
        baud_rate=9600,
        data_bits=7,
        parity="E",
        stop_bits=2,
        flow_control=FlowControl.RTS_CTS,
    )
    restored = SerialConfig.from_dict(config.to_dict())
    assert restored == config
