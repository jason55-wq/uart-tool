from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QByteArray, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.command_template import CommandTemplate
from models.enums import ConnectionState, DisplayMode, FlowControl, SendMode
from models.serial_config import SerialConfig
from models.serial_event import SerialEvent
from ui.template_dialog import TemplateEditDialog


class MainWindow(QMainWindow):
    """Main product window for UART monitoring workflows."""

    refresh_requested = pyqtSignal()
    connect_requested = pyqtSignal()
    send_requested = pyqtSignal(str, SendMode)
    clear_requested = pyqtSignal()
    display_mode_changed = pyqtSignal(DisplayMode)
    logging_toggled = pyqtSignal(bool)
    periodic_send_toggled = pyqtSignal(bool, int)
    search_requested = pyqtSignal(str)
    template_add_requested = pyqtSignal()
    template_edit_requested = pyqtSignal(str)
    template_delete_requested = pyqtSignal(str)
    template_send_requested = pyqtSignal(str)
    window_closing = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UART Serial Monitor")
        self.resize(1280, 820)
        self._messages: list[SerialEvent] = []
        self._history: list[str] = []
        self._controller = None

        self._build_ui()
        self._build_status_bar()
        self._bind_reformat_triggers()

    def set_controller(self, controller) -> None:
        self._controller = controller

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_connection_panel())
        root_layout.addWidget(self._build_center_panel(), stretch=1)
        root_layout.addWidget(self._build_sender_panel())

        self.setCentralWidget(root)

    def _bind_reformat_triggers(self) -> None:
        self.timestamp_check.toggled.connect(lambda _: self.reformat_messages(self.current_display_mode()))
        self.direction_check.toggled.connect(lambda _: self.reformat_messages(self.current_display_mode()))
        self.newline_combo.currentTextChanged.connect(lambda _: self.reformat_messages(self.current_display_mode()))

    def _build_connection_panel(self) -> QWidget:
        box = QGroupBox("Connection")
        layout = QGridLayout(box)

        self.port_combo = QComboBox()
        self.refresh_button = QToolButton(text="Refresh")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")

        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText("8")

        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O", "M", "S"])

        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])

        self.flow_control_combo = QComboBox()
        self.flow_control_combo.addItems([item.value for item in FlowControl])

        self.connect_button = QPushButton("Open")
        self.connect_button.clicked.connect(self.connect_requested.emit)

        layout.addWidget(QLabel("Port"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1)
        layout.addWidget(self.refresh_button, 0, 2)
        layout.addWidget(QLabel("Baud"), 0, 3)
        layout.addWidget(self.baud_combo, 0, 4)
        layout.addWidget(QLabel("Data Bits"), 0, 5)
        layout.addWidget(self.data_bits_combo, 0, 6)
        layout.addWidget(QLabel("Parity"), 1, 0)
        layout.addWidget(self.parity_combo, 1, 1)
        layout.addWidget(QLabel("Stop Bits"), 1, 2)
        layout.addWidget(self.stop_bits_combo, 1, 3)
        layout.addWidget(QLabel("Flow Control"), 1, 4)
        layout.addWidget(self.flow_control_combo, 1, 5)
        layout.addWidget(self.connect_button, 1, 6)
        return box

    def _build_center_panel(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_receive_panel())
        splitter.addWidget(self._build_template_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        return splitter

    def _build_receive_panel(self) -> QWidget:
        box = QGroupBox("Receive Monitor")
        layout = QVBoxLayout(box)

        toolbar = QHBoxLayout()
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems([item.value for item in DisplayMode])
        self.display_mode_combo.currentTextChanged.connect(
            lambda value: self.display_mode_changed.emit(DisplayMode(value))
        )

        self.timestamp_check = QCheckBox("Timestamp")
        self.timestamp_check.setChecked(True)
        self.direction_check = QCheckBox("RX/TX")
        self.direction_check.setChecked(True)
        self.auto_scroll_check = QCheckBox("Auto Scroll")
        self.auto_scroll_check.setChecked(True)
        self.log_check = QCheckBox("Record Log")
        self.log_check.toggled.connect(self.logging_toggled.emit)

        self.newline_combo = QComboBox()
        self.newline_combo.addItems(["\\n", "\\r\\n", "none"])

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search / highlight")
        self.search_edit.textChanged.connect(self.search_requested.emit)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_requested.emit)

        toolbar.addWidget(QLabel("Display"))
        toolbar.addWidget(self.display_mode_combo)
        toolbar.addWidget(self.timestamp_check)
        toolbar.addWidget(self.direction_check)
        toolbar.addWidget(self.auto_scroll_check)
        toolbar.addWidget(QLabel("Line End"))
        toolbar.addWidget(self.newline_combo)
        toolbar.addWidget(self.log_check)
        toolbar.addStretch(1)
        toolbar.addWidget(self.search_edit)
        toolbar.addWidget(self.clear_button)

        self.receive_text = QPlainTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        layout.addLayout(toolbar)
        layout.addWidget(self.receive_text, stretch=1)
        return box

    def _build_template_panel(self) -> QWidget:
        box = QGroupBox("Command Templates")
        layout = QVBoxLayout(box)

        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(lambda _: self._emit_selected_template_send())

        buttons = QHBoxLayout()
        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        send_button = QPushButton("Send")
        add_button.clicked.connect(self.template_add_requested.emit)
        edit_button.clicked.connect(self._emit_selected_template_edit)
        delete_button.clicked.connect(self._emit_selected_template_delete)
        send_button.clicked.connect(self._emit_selected_template_send)

        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(send_button)

        layout.addWidget(self.template_list)
        layout.addLayout(buttons)
        return box

    def _build_sender_panel(self) -> QWidget:
        box = QGroupBox("Send")
        layout = QVBoxLayout(box)

        row1 = QHBoxLayout()
        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItems([item.value for item in SendMode])
        self.enter_send_check = QCheckBox("Enter to Send")
        self.history_combo = QComboBox()
        self.history_combo.setEditable(False)
        self.history_combo.currentTextChanged.connect(self._load_history_to_editor)

        row1.addWidget(QLabel("Mode"))
        row1.addWidget(self.send_mode_combo)
        row1.addWidget(self.enter_send_check)
        row1.addWidget(QLabel("History"))
        row1.addWidget(self.history_combo, stretch=1)

        row2 = QHBoxLayout()
        self.send_text = QPlainTextEdit()
        self.send_text.setPlaceholderText("Type payload here")
        self.send_text.setFixedHeight(110)

        right_box = QVBoxLayout()
        self.send_button = QPushButton("Send Now")
        self.send_button.clicked.connect(self._emit_send)
        self.periodic_check = QCheckBox("Periodic")
        self.periodic_check.toggled.connect(self._emit_periodic_toggle)
        self.periodic_spin = QSpinBox()
        self.periodic_spin.setRange(10, 60000)
        self.periodic_spin.setValue(1000)
        self.periodic_spin.setSuffix(" ms")
        right_box.addWidget(self.send_button)
        right_box.addWidget(self.periodic_check)
        right_box.addWidget(self.periodic_spin)
        right_box.addStretch(1)

        row2.addWidget(self.send_text, stretch=1)
        row2.addLayout(right_box)

        layout.addLayout(row1)
        layout.addLayout(row2)
        return box

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.connection_label = QLabel("Disconnected")
        self.counter_label = QLabel("RX 0 B | TX 0 B | RX pkt 0 | TX pkt 0")
        self.mode_label = QLabel("Display ASCII")
        self.logging_label = QLabel("Log Off")
        status.addPermanentWidget(self.connection_label)
        status.addPermanentWidget(self.counter_label)
        status.addPermanentWidget(self.mode_label)
        status.addPermanentWidget(self.logging_label)
        self.setStatusBar(status)

    def build_serial_config(self) -> SerialConfig:
        return SerialConfig(
            port=self.port_combo.currentText(),
            baud_rate=int(self.baud_combo.currentText()),
            data_bits=int(self.data_bits_combo.currentText()),
            parity=self.parity_combo.currentText(),
            stop_bits=float(self.stop_bits_combo.currentText()),
            flow_control=FlowControl(self.flow_control_combo.currentText()),
        )

    def populate_serial_config(self, config: SerialConfig) -> None:
        self._set_combo_text(self.port_combo, config.port)
        self._set_combo_text(self.baud_combo, str(config.baud_rate))
        self._set_combo_text(self.data_bits_combo, str(config.data_bits))
        self._set_combo_text(self.parity_combo, config.parity)
        stop_bits_text = str(config.stop_bits).rstrip("0").rstrip(".")
        self._set_combo_text(self.stop_bits_combo, stop_bits_text)
        self._set_combo_text(self.flow_control_combo, config.flow_control.value)

    def refresh_ports(self, ports: list[str]) -> None:
        current = self.port_combo.currentText()
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self._set_combo_text(self.port_combo, current or (ports[0] if ports else ""))
        self.port_combo.blockSignals(False)

    def append_serial_event(self, event: SerialEvent, rendered: str) -> None:
        self._messages.append(event)
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(rendered)
        if self.auto_scroll_check.isChecked():
            self.receive_text.moveCursor(QTextCursor.MoveOperation.End)
        self.highlight_search(self.search_edit.text())

    def reformat_messages(self, _: DisplayMode) -> None:
        if not self._controller:
            return
        self.receive_text.clear()
        parser = self._controller.parser_registry.get_parser(self.current_display_mode())
        for event in self._messages:
            self.receive_text.insertPlainText(parser.render(event, self.current_view_options()))
        self.highlight_search(self.search_edit.text())

    def clear_receive_view(self) -> None:
        self._messages.clear()
        self.receive_text.clear()

    def current_display_mode(self) -> DisplayMode:
        return DisplayMode(self.display_mode_combo.currentText())

    def current_view_options(self) -> dict:
        return {
            "show_timestamp": self.timestamp_check.isChecked(),
            "show_direction": self.direction_check.isChecked(),
            "newline": self.newline_combo.currentText(),
        }

    def periodic_payload(self) -> tuple[str, SendMode]:
        return self.send_text.toPlainText(), SendMode(self.send_mode_combo.currentText())

    def update_connection_state(self, state: ConnectionState, reason: str = "") -> None:
        self.connection_label.setText(state.value if not reason else f"{state.value}: {reason}")
        self.connect_button.setText("Close" if state == ConnectionState.CONNECTED else "Open")

    def update_counters(self, rx_bytes: int, tx_bytes: int, rx_packets: int, tx_packets: int) -> None:
        self.counter_label.setText(
            f"RX {rx_bytes} B | TX {tx_bytes} B | RX pkt {rx_packets} | TX pkt {tx_packets}"
        )

    def update_display_mode(self, mode: DisplayMode) -> None:
        self.mode_label.setText(f"Display {mode.value}")

    def update_logging_state(self, enabled: bool) -> None:
        self.logging_label.setText("Log On" if enabled else "Log Off")
        self.log_check.blockSignals(True)
        self.log_check.setChecked(enabled)
        self.log_check.blockSignals(False)

    def update_periodic_state(self, enabled: bool) -> None:
        self.periodic_check.blockSignals(True)
        self.periodic_check.setChecked(enabled)
        self.periodic_check.blockSignals(False)

    def status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def push_send_history(self, payload: str) -> None:
        payload = payload.strip()
        if not payload:
            return
        if payload in self._history:
            self._history.remove(payload)
        self._history.insert(0, payload)
        self.set_send_history(self._history)

    def set_send_history(self, history: list[str]) -> None:
        self._history = history[:30]
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItems(self._history)
        self.history_combo.blockSignals(False)

    def send_history(self) -> list[str]:
        return list(self._history)

    def set_command_templates(self, templates: list[CommandTemplate]) -> None:
        self.template_list.clear()
        for template in templates:
            item = QListWidgetItem(f"[{template.category}] {template.name}")
            item.setData(Qt.ItemDataRole.UserRole, template.template_id)
            item.setToolTip(template.payload)
            self.template_list.addItem(item)

    def edit_template_dialog(self, template: Optional[CommandTemplate] = None) -> Optional[CommandTemplate]:
        dialog = TemplateEditDialog(self, template)
        if dialog.exec():
            return dialog.build_template()
        return None

    def confirm_template_delete(self, template_name: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Delete Template",
            f"Delete template '{template_name}'?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def load_template_to_sender(self, template: CommandTemplate) -> None:
        self.send_text.setPlainText(template.payload)
        self.send_mode_combo.setCurrentText(template.mode.value)

    def apply_settings(self, state: dict) -> None:
        if geometry := state.get("geometry"):
            self.restoreGeometry(QByteArray.fromHex(geometry.encode("ascii")))
        self.display_mode_combo.setCurrentText(state.get("display_mode", DisplayMode.ASCII.value))
        self.send_mode_combo.setCurrentText(state.get("send_mode", SendMode.ASCII.value))
        self.enter_send_check.setChecked(bool(state.get("enter_send", False)))
        self.timestamp_check.setChecked(bool(state.get("show_timestamp", True)))
        self.direction_check.setChecked(bool(state.get("show_direction", True)))
        self.auto_scroll_check.setChecked(bool(state.get("auto_scroll", True)))
        self.newline_combo.setCurrentText(state.get("newline", "\\n"))
        self.periodic_spin.setValue(int(state.get("periodic_interval", 1000)))

    def collect_ui_state(self) -> dict:
        return {
            "geometry": bytes(self.saveGeometry().toHex()).decode("ascii"),
            "display_mode": self.display_mode_combo.currentText(),
            "send_mode": self.send_mode_combo.currentText(),
            "enter_send": self.enter_send_check.isChecked(),
            "show_timestamp": self.timestamp_check.isChecked(),
            "show_direction": self.direction_check.isChecked(),
            "auto_scroll": self.auto_scroll_check.isChecked(),
            "newline": self.newline_combo.currentText(),
            "periodic_interval": self.periodic_spin.value(),
        }

    def highlight_search(self, keyword: str) -> None:
        selections = []
        if keyword:
            document = self.receive_text.document()
            cursor = document.find(keyword)
            while not cursor.isNull():
                selection = QTextEdit.ExtraSelection()
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#f7d774"))
                selection.cursor = cursor
                selection.format = fmt
                selections.append(selection)
                cursor = document.find(keyword, cursor)
        self.receive_text.setExtraSelections(selections)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.window_closing.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if (
            self.enter_send_check.isChecked()
            and self.send_text.hasFocus()
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ):
            self._emit_send()
            event.accept()
            return
        super().keyPressEvent(event)

    def _emit_send(self) -> None:
        self.send_requested.emit(self.send_text.toPlainText(), SendMode(self.send_mode_combo.currentText()))

    def _emit_periodic_toggle(self, checked: bool) -> None:
        self.periodic_send_toggled.emit(checked, self.periodic_spin.value())

    def _emit_selected_template_edit(self) -> None:
        item = self.template_list.currentItem()
        if item:
            self.template_edit_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _emit_selected_template_delete(self) -> None:
        item = self.template_list.currentItem()
        if item:
            self.template_delete_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _emit_selected_template_send(self) -> None:
        item = self.template_list.currentItem()
        if item:
            self.template_send_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _load_history_to_editor(self, value: str) -> None:
        if value:
            self.send_text.setPlainText(value)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif value:
            combo.addItem(value)
            combo.setCurrentText(value)

