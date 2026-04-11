from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from controllers.main_controller import MainController
from services.command_repository import CommandRepository
from services.log_service import LogService
from services.parser_service import ParserRegistry
from services.serial_service import SerialService
from services.settings_service import SettingsService
from ui.main_window import MainWindow


def _load_stylesheet() -> str:
    resources_dir = Path(__file__).resolve().parent.parent / "resources"
    qss_path = resources_dir / "styles.qss"
    if not qss_path.exists():
        return ""
    stylesheet = qss_path.read_text(encoding="utf-8")
    bg_path = (resources_dir / "cartoon_bg.svg").as_uri()
    return stylesheet.replace('url("cartoon_bg.svg")', f'url("{bg_path}")')


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("UART 序列監控器")
    app.setOrganizationName("CodexLab")
    app.setStyleSheet(_load_stylesheet())

    settings_service = SettingsService()
    command_repository = CommandRepository()
    parser_registry = ParserRegistry()
    log_service = LogService()
    serial_service = SerialService()

    window = MainWindow()
    controller = MainController(
        window=window,
        serial_service=serial_service,
        settings_service=settings_service,
        command_repository=command_repository,
        parser_registry=parser_registry,
        log_service=log_service,
    )
    window.set_controller(controller)
    controller.initialize()
    window.show()

    exit_code = app.exec()
    controller.shutdown()
    return exit_code
