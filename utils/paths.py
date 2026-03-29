from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QStandardPaths


def app_data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path
