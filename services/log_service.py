from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.serial_event import SerialEvent
from utils.paths import app_data_dir


class LogService:
    """Persists TX/RX events independently from what the UI renders."""

    def __init__(self) -> None:
        self._handle = None
        self._current_path: Optional[Path] = None

    @property
    def is_active(self) -> bool:
        return self._handle is not None

    def start(self, target_path: Optional[Path] = None) -> Path:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self._current_path = target_path or log_dir / f"uart_{datetime.now():%Y%m%d_%H%M%S}.log"
        self._handle = self._current_path.open("a", encoding="utf-8")
        return self._current_path

    def stop(self) -> None:
        if self._handle:
            self._handle.close()
        self._handle = None

    def log_event(self, event: SerialEvent) -> None:
        if not self._handle:
            return
        record = {
            "timestamp": event.timestamp.isoformat(timespec="milliseconds"),
            "direction": event.direction,
            "hex": event.payload.hex(" "),
            "raw_len": len(event.payload),
        }
        self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._handle.flush()
