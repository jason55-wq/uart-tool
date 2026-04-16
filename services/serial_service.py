from __future__ import annotations

from typing import Optional

import serial
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from serial.tools import list_ports

from models.enums import ConnectionState, FlowControl
from models.serial_config import SerialConfig
from models.serial_event import SerialEvent


class SerialReaderWorker(QObject):
    """Worker that continuously reads bytes from an opened serial port."""

    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    disconnected = pyqtSignal(str)

    def __init__(self, serial_port: serial.Serial) -> None:
        super().__init__()
        self._serial = serial_port
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                if self._serial.in_waiting:
                    payload = self._serial.read(self._serial.in_waiting)
                    if payload:
                        self.data_received.emit(payload)
                else:
                    self._serial.timeout = 0.2
                    payload = self._serial.read(1)
                    if payload:
                        more = self._serial.read(self._serial.in_waiting)
                        self.data_received.emit(payload + more)
            except serial.SerialException as exc:
                self.disconnected.emit(str(exc))
                break
            except Exception as exc:  # noqa: BLE001
                self.error_occurred.emit(str(exc))
                break


class SerialService(QObject):
    """Serial abstraction kept independent from UI widgets."""

    data_received = pyqtSignal(SerialEvent)
    data_sent = pyqtSignal(SerialEvent)
    error_occurred = pyqtSignal(str)
    connection_state_changed = pyqtSignal(ConnectionState, str)

    def __init__(self) -> None:
        super().__init__()
        self._serial: Optional[serial.Serial] = None
        self._worker: Optional[SerialReaderWorker] = None
        self._thread: Optional[QThread] = None
        self._state = ConnectionState.DISCONNECTED
        self.rx_bytes = 0
        self.tx_bytes = 0

    @property
    def connection_state(self) -> ConnectionState:
        return self._state

    def list_ports(self) -> list[str]:
        return [port.device for port in list_ports.comports()]

    def open(self, config: SerialConfig) -> None:
        if not config.port:
            raise ValueError("請先選擇串口。")
        if self._serial and self._serial.is_open:
            self.close()

        self._set_state(ConnectionState.CONNECTING, f"正在開啟 {config.port}...")
        try:
            self._serial = serial.Serial(
                port=config.port,
                baudrate=config.baud_rate,
                bytesize=self._map_bytesize(config.data_bits),
                parity=self._map_parity(config.parity),
                stopbits=self._map_stopbits(config.stop_bits),
                xonxoff=config.flow_control == FlowControl.XON_XOFF,
                rtscts=config.flow_control == FlowControl.RTS_CTS,
                timeout=0.2,
            )
        except (serial.SerialException, KeyError) as exc:
            self._serial = None
            self._set_state(ConnectionState.ERROR, "開啟失敗")
            raise RuntimeError(f"開啟串口失敗：{exc}") from exc

        self.rx_bytes = 0
        self.tx_bytes = 0
        self._worker = SerialReaderWorker(self._serial)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.data_received.connect(self._on_data_received)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.disconnected.connect(self._on_worker_disconnected)
        self._thread.start()
        self._set_state(ConnectionState.CONNECTED, "連線成功")

    def close(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(1000)
            self._thread = None
        if self._serial:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except serial.SerialException as exc:
                self.error_occurred.emit(str(exc))
            self._serial = None
        self._worker = None
        self._set_state(ConnectionState.DISCONNECTED, "串口已關閉")

    def send(self, payload: bytes) -> None:
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("串口尚未開啟。")
        try:
            written = self._serial.write(payload)
            self.tx_bytes += written
            self.data_sent.emit(SerialEvent(direction="TX", payload=payload[:written]))
        except serial.SerialException as exc:
            raise RuntimeError(f"發送資料失敗：{exc}") from exc

    def _on_data_received(self, payload: bytes) -> None:
        self.rx_bytes += len(payload)
        self.data_received.emit(SerialEvent(direction="RX", payload=payload))

    def _on_worker_disconnected(self, message: str) -> None:
        self.close()
        self._set_state(ConnectionState.ERROR, "裝置已中斷連線")
        self.error_occurred.emit(f"串口裝置已中斷連線：{message}")

    def _set_state(self, state: ConnectionState, reason: str) -> None:
        self._state = state
        self.connection_state_changed.emit(state, reason)

    @staticmethod
    def _map_bytesize(data_bits: int):
        mapping = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS,
        }
        return mapping[data_bits]

    @staticmethod
    def _map_parity(parity: str):
        mapping = {
            "N": serial.PARITY_NONE,
            "E": serial.PARITY_EVEN,
            "O": serial.PARITY_ODD,
            "M": serial.PARITY_MARK,
            "S": serial.PARITY_SPACE,
        }
        return mapping[parity]

    @staticmethod
    def _map_stopbits(stop_bits: float):
        mapping = {
            1.0: serial.STOPBITS_ONE,
            1.5: serial.STOPBITS_ONE_POINT_FIVE,
            2.0: serial.STOPBITS_TWO,
        }
        return mapping[stop_bits]
