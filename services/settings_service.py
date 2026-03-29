from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QSettings

from models.serial_config import SerialConfig
from utils.paths import app_data_dir


class SettingsService:
    """Stores persistent application settings and lightweight user state."""

    def __init__(self) -> None:
        self._settings = QSettings("CodexLab", "UARTSerialMonitor")
        self._history_path = app_data_dir() / "send_history.json"

    def load_serial_config(self) -> SerialConfig:
        payload = self._settings.value("serial/config", {}, type=dict)
        return SerialConfig.from_dict(payload or {})

    def save_serial_config(self, config: SerialConfig) -> None:
        self._settings.setValue("serial/config", config.to_dict())

    def load_ui_state(self) -> dict:
        return self._settings.value("ui/state", {}, type=dict) or {}

    def save_ui_state(self, state: dict) -> None:
        self._settings.setValue("ui/state", state)

    def load_send_history(self) -> list[str]:
        if not self._history_path.exists():
            return []
        try:
            return json.loads(self._history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def save_send_history(self, history: list[str]) -> None:
        self._history_path.write_text(
            json.dumps(history[:30], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
