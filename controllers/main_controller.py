from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QMessageBox

from models.enums import ConnectionState, SendMode
from services.command_repository import CommandRepository
from services.log_service import LogService
from services.parser_service import ParserRegistry
from services.serial_service import SerialService
from services.settings_service import SettingsService
from utils.encoding import encode_payload


class MainController(QObject):
    """Coordinates UI, serial I/O, persistence, and business workflows."""

    def __init__(
        self,
        window,
        serial_service: SerialService,
        settings_service: SettingsService,
        command_repository: CommandRepository,
        parser_registry: ParserRegistry,
        log_service: LogService,
    ) -> None:
        super().__init__()
        self.window = window
        self.serial_service = serial_service
        self.settings_service = settings_service
        self.command_repository = command_repository
        self.parser_registry = parser_registry
        self.log_service = log_service

        self._rx_packets = 0
        self._tx_packets = 0
        self._periodic_timer = QTimer(self)
        self._periodic_timer.setSingleShot(False)
        self._periodic_timer.timeout.connect(self._send_periodic_payload)
        self._state = ConnectionState.DISCONNECTED

    def initialize(self) -> None:
        self._bind_signals()
        self.window.apply_settings(self.settings_service.load_ui_state())
        self.window.set_command_templates(self.command_repository.list_templates())
        self.window.set_send_history(self.settings_service.load_send_history())
        self.window.populate_serial_config(self.settings_service.load_serial_config())
        self.window.refresh_ports(self.serial_service.list_ports())
        self.window.update_connection_state(self._state)
        self.window.update_counters(0, 0, 0, 0)
        self.window.update_logging_state(self.log_service.is_active)
        self.window.update_display_mode(self.window.current_display_mode())

    def shutdown(self) -> None:
        self._periodic_timer.stop()
        self._persist_ui_state()
        if self.serial_service.connection_state == ConnectionState.CONNECTED:
            self.serial_service.close()
        self.log_service.stop()

    def _bind_signals(self) -> None:
        self.window.refresh_requested.connect(self._refresh_ports)
        self.window.connect_requested.connect(self._toggle_connection)
        self.window.send_requested.connect(self.send_once)
        self.window.clear_requested.connect(self.window.clear_receive_view)
        self.window.display_mode_changed.connect(self.window.update_display_mode)
        self.window.display_mode_changed.connect(self.window.reformat_messages)
        self.window.search_requested.connect(self.window.highlight_search)
        self.window.logging_toggled.connect(self._toggle_logging)
        self.window.periodic_send_toggled.connect(self._toggle_periodic_send)
        self.window.template_add_requested.connect(self._add_template)
        self.window.template_edit_requested.connect(self._edit_template)
        self.window.template_delete_requested.connect(self._delete_template)
        self.window.template_send_requested.connect(self._send_template)
        self.window.window_closing.connect(self._persist_ui_state)

        self.serial_service.data_received.connect(self._handle_serial_event)
        self.serial_service.data_sent.connect(self._handle_serial_event)
        self.serial_service.error_occurred.connect(self._handle_error)
        self.serial_service.connection_state_changed.connect(self._handle_connection_state)

    def _persist_ui_state(self) -> None:
        self.settings_service.save_serial_config(self.window.build_serial_config())
        self.settings_service.save_ui_state(self.window.collect_ui_state())
        self.settings_service.save_send_history(self.window.send_history())

    def _refresh_ports(self) -> None:
        self.window.refresh_ports(self.serial_service.list_ports())

    def _toggle_connection(self) -> None:
        if self.serial_service.connection_state == ConnectionState.CONNECTED:
            self.serial_service.close()
            return

        config = self.window.build_serial_config()
        try:
            self.serial_service.open(config)
            self.settings_service.save_serial_config(config)
        except Exception as exc:  # noqa: BLE001
            self._handle_error(str(exc))

    def send_once(self, payload: str, mode: SendMode) -> None:
        if self.serial_service.connection_state != ConnectionState.CONNECTED:
            self._handle_error("Serial port is not connected.")
            return

        try:
            raw_bytes = encode_payload(payload, mode)
        except ValueError as exc:
            self._handle_error(str(exc))
            return

        if not raw_bytes:
            return
        try:
            self.serial_service.send(raw_bytes)
        except Exception as exc:  # noqa: BLE001
            self._handle_error(str(exc))
            return
        self.window.push_send_history(payload)
        self.settings_service.save_send_history(self.window.send_history())

    def _toggle_logging(self, enabled: bool) -> None:
        if enabled:
            self.log_service.start()
        else:
            self.log_service.stop()
        self.window.update_logging_state(self.log_service.is_active)

    def _toggle_periodic_send(self, enabled: bool, interval_ms: int) -> None:
        if enabled:
            self._periodic_timer.start(max(interval_ms, 10))
        else:
            self._periodic_timer.stop()
        self.window.update_periodic_state(enabled)

    def _send_periodic_payload(self) -> None:
        payload, mode = self.window.periodic_payload()
        self.send_once(payload, mode)

    def _handle_serial_event(self, event) -> None:
        if event.direction == "RX":
            self._rx_packets += 1
        else:
            self._tx_packets += 1

        parser = self.parser_registry.get_parser(self.window.current_display_mode())
        rendered = parser.render(event, self.window.current_view_options())
        self.window.append_serial_event(event, rendered)
        self.window.update_counters(
            self.serial_service.rx_bytes,
            self.serial_service.tx_bytes,
            self._rx_packets,
            self._tx_packets,
        )
        self.log_service.log_event(event)

    def _handle_error(self, message: str) -> None:
        self.window.status_message(message)
        QMessageBox.warning(self.window, "UART Monitor", message)

    def _handle_connection_state(self, state: ConnectionState, reason: str) -> None:
        self._state = state
        self.window.update_connection_state(state, reason)
        if state != ConnectionState.CONNECTED:
            self._periodic_timer.stop()
            self.window.update_periodic_state(False)

    def _add_template(self) -> None:
        template = self.window.edit_template_dialog()
        if template:
            self.command_repository.add_template(template)
            self.window.set_command_templates(self.command_repository.list_templates())

    def _edit_template(self, template_id: str) -> None:
        template = self.command_repository.get_template(template_id)
        if template is None:
            return
        updated = self.window.edit_template_dialog(template)
        if updated:
            self.command_repository.update_template(updated)
            self.window.set_command_templates(self.command_repository.list_templates())

    def _delete_template(self, template_id: str) -> None:
        template = self.command_repository.get_template(template_id)
        if template is None:
            return
        if self.window.confirm_template_delete(template.name):
            self.command_repository.delete_template(template_id)
            self.window.set_command_templates(self.command_repository.list_templates())

    def _send_template(self, template_id: str) -> None:
        template = self.command_repository.get_template(template_id)
        if template is None:
            return
        self.window.load_template_to_sender(template)
        self.send_once(template.payload, template.mode)
