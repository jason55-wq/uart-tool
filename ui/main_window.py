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

    _DISPLAY_MODE_LABELS = {
        DisplayMode.ASCII: "ASCII 顯示",
        DisplayMode.HEX: "十六進位顯示",
        DisplayMode.UTF8: "UTF-8 顯示",
    }
    _SEND_MODE_LABELS = {
        SendMode.ASCII: "ASCII 文字",
        SendMode.HEX: "十六進位",
    }
    _FLOW_CONTROL_LABELS = {
        FlowControl.NONE: "無",
        FlowControl.RTS_CTS: "RTS/CTS",
        FlowControl.XON_XOFF: "XON/XOFF",
    }
    _CONNECTION_STATE_LABELS = {
        ConnectionState.DISCONNECTED: "未連線",
        ConnectionState.CONNECTING: "連線中",
        ConnectionState.CONNECTED: "已連線",
        ConnectionState.ERROR: "錯誤",
    }

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
        self.setWindowTitle("UART 序列監控器")
        self.resize(1280, 820)
        self._messages: list[SerialEvent] = []
        self._history: list[str] = []
        self._advanced_widgets: list[QWidget] = []
        self._controller = None

        self._build_ui()
        self._build_status_bar()
        self._set_advanced_visibility(False)
        self._bind_reformat_triggers()

    def set_controller(self, controller) -> None:
        self._controller = controller

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_connection_panel())
        root_layout.addWidget(self._build_advanced_toggle_row())
        root_layout.addWidget(self._build_center_panel(), stretch=1)
        root_layout.addWidget(self._build_sender_panel())

        self.setCentralWidget(root)

    def _build_advanced_toggle_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        self.advanced_toggle_button = QToolButton(text="顯示進階功能")
        self.advanced_toggle_button.setCheckable(True)
        self.advanced_toggle_button.toggled.connect(self._set_advanced_visibility)
        layout.addWidget(self.advanced_toggle_button)
        return row

    def _bind_reformat_triggers(self) -> None:
        self.timestamp_check.toggled.connect(lambda _: self.reformat_messages(self.current_display_mode()))
        self.direction_check.toggled.connect(lambda _: self.reformat_messages(self.current_display_mode()))
        self.newline_combo.currentTextChanged.connect(lambda _: self.reformat_messages(self.current_display_mode()))

    def _build_connection_panel(self) -> QWidget:
        box = QGroupBox("連線設定")
        layout = QGridLayout(box)

        self.port_combo = QComboBox()
        self.refresh_button = QToolButton(text="重新整理")
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
        for item, label in self._FLOW_CONTROL_LABELS.items():
            self.flow_control_combo.addItem(label, item.value)

        self.connect_button = QPushButton("開啟")
        self.connect_button.clicked.connect(self.connect_requested.emit)

        layout.addWidget(QLabel("埠號"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1)
        layout.addWidget(self.refresh_button, 0, 2)
        layout.addWidget(QLabel("鮑率"), 0, 3)
        layout.addWidget(self.baud_combo, 0, 4)
        layout.addWidget(QLabel("資料位元"), 0, 5)
        layout.addWidget(self.data_bits_combo, 0, 6)
        layout.addWidget(QLabel("同位元"), 1, 0)
        layout.addWidget(self.parity_combo, 1, 1)
        layout.addWidget(QLabel("停止位元"), 1, 2)
        layout.addWidget(self.stop_bits_combo, 1, 3)
        layout.addWidget(QLabel("流量控制"), 1, 4)
        layout.addWidget(self.flow_control_combo, 1, 5)
        layout.addWidget(self.connect_button, 1, 6)
        return box

    def _build_center_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_receive_panel(), stretch=1)
        layout.addWidget(self._build_template_panel())
        return container

    def _build_receive_panel(self) -> QWidget:
        box = QGroupBox("接收監看")
        layout = QVBoxLayout(box)

        self.display_mode_combo = QComboBox()
        for item, label in self._DISPLAY_MODE_LABELS.items():
            self.display_mode_combo.addItem(label, item.value)
        self.display_mode_combo.currentIndexChanged.connect(
            lambda _: self.display_mode_changed.emit(self.current_display_mode())
        )

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("顯示"))
        toolbar.addWidget(self.display_mode_combo)

        self.auto_scroll_check = QCheckBox("自動捲動")
        self.auto_scroll_check.setChecked(True)
        toolbar.addWidget(self.auto_scroll_check)
        toolbar.addStretch(1)

        self.clear_button = QPushButton("清除")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        toolbar.addWidget(self.clear_button)

        advanced = QWidget()
        advanced_layout = QHBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)

        self.timestamp_check = QCheckBox("時間戳記")
        self.timestamp_check.setChecked(True)
        self.direction_check = QCheckBox("收發標記")
        self.direction_check.setChecked(True)
        self.log_check = QCheckBox("記錄日誌")
        self.log_check.toggled.connect(self.logging_toggled.emit)

        self.newline_combo = QComboBox()
        self.newline_combo.addItem("換行 (LF)", "\n")
        self.newline_combo.addItem("回車換行 (CRLF)", "\r\n")
        self.newline_combo.addItem("無", "none")

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜尋 / 標示")
        self.search_edit.textChanged.connect(self.search_requested.emit)

        advanced_layout.addWidget(self.timestamp_check)
        advanced_layout.addWidget(self.direction_check)
        advanced_layout.addWidget(QLabel("換行格式"))
        advanced_layout.addWidget(self.newline_combo)
        advanced_layout.addWidget(self.log_check)
        advanced_layout.addWidget(self.search_edit, stretch=1)

        self.receive_text = QPlainTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        layout.addLayout(toolbar)
        layout.addWidget(advanced)
        layout.addWidget(self.receive_text, stretch=1)
        self._advanced_widgets.append(advanced)
        return box

    def _build_template_panel(self) -> QWidget:
        box = QGroupBox("命令模板")
        layout = QVBoxLayout(box)

        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(lambda _: self._emit_selected_template_send())

        buttons = QHBoxLayout()
        add_button = QPushButton("新增")
        edit_button = QPushButton("編輯")
        delete_button = QPushButton("刪除")
        send_button = QPushButton("送出")
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
        self._advanced_widgets.append(box)
        return box

    def _build_sender_panel(self) -> QWidget:
        box = QGroupBox("發送")
        layout = QVBoxLayout(box)

        row2 = QHBoxLayout()
        self.send_text = QPlainTextEdit()
        self.send_text.setPlaceholderText("請在這裡輸入資料內容")
        self.send_text.setFixedHeight(110)

        right_box = QVBoxLayout()
        self.send_button = QPushButton("立即送出")
        self.send_button.clicked.connect(self._emit_send)
        self.periodic_check = QCheckBox("週期發送")
        self.periodic_check.toggled.connect(self._emit_periodic_toggle)
        self.periodic_spin = QSpinBox()
        self.periodic_spin.setRange(10, 60000)
        self.periodic_spin.setValue(1000)
        self.periodic_spin.setSuffix(" ms")
        right_box.addWidget(self.send_button)
        right_box.addStretch(1)

        row2.addWidget(self.send_text, stretch=1)
        row2.addLayout(right_box)

        advanced = QWidget()
        advanced_layout = QHBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)

        self.send_mode_combo = QComboBox()
        for item, label in self._SEND_MODE_LABELS.items():
            self.send_mode_combo.addItem(label, item.value)
        self.enter_send_check = QCheckBox("Enter 送出")
        self.history_combo = QComboBox()
        self.history_combo.setEditable(False)
        self.history_combo.currentTextChanged.connect(self._load_history_to_editor)

        advanced_layout.addWidget(QLabel("模式"))
        advanced_layout.addWidget(self.send_mode_combo)
        advanced_layout.addWidget(self.enter_send_check)
        advanced_layout.addWidget(QLabel("歷史紀錄"))
        advanced_layout.addWidget(self.history_combo, stretch=1)
        advanced_layout.addWidget(QLabel("週期"))
        advanced_layout.addWidget(self.periodic_check)
        advanced_layout.addWidget(self.periodic_spin)

        layout.addWidget(advanced)
        layout.addLayout(row2)
        self._advanced_widgets.append(advanced)
        return box

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.connection_label = QLabel("未連線")
        self.counter_label = QLabel("RX 0 B | TX 0 B | RX 封包 0 | TX 封包 0")
        self.mode_label = QLabel("顯示：ASCII 顯示")
        self.logging_label = QLabel("日誌關閉")
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
            flow_control=FlowControl(self.flow_control_combo.currentData() or self.flow_control_combo.currentText()),
        )

    def populate_serial_config(self, config: SerialConfig) -> None:
        self._set_combo_text(self.port_combo, config.port)
        self._set_combo_text(self.baud_combo, str(config.baud_rate))
        self._set_combo_text(self.data_bits_combo, str(config.data_bits))
        self._set_combo_text(self.parity_combo, config.parity)
        stop_bits_text = str(config.stop_bits).rstrip("0").rstrip(".")
        self._set_combo_text(self.stop_bits_combo, stop_bits_text)
        self._set_combo_value(self.flow_control_combo, config.flow_control.value)

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
        return DisplayMode(self.display_mode_combo.currentData() or DisplayMode.ASCII.value)

    def current_view_options(self) -> dict:
        return {
            "show_timestamp": self.timestamp_check.isChecked(),
            "show_direction": self.direction_check.isChecked(),
            "newline": self.newline_combo.currentData() or "\n",
        }

    def periodic_payload(self) -> tuple[str, SendMode]:
        return self.send_text.toPlainText(), SendMode(self.send_mode_combo.currentData() or SendMode.ASCII.value)

    def update_connection_state(self, state: ConnectionState, reason: str = "") -> None:
        label = self._CONNECTION_STATE_LABELS[state]
        self.connection_label.setText(label if not reason else f"{label}：{reason}")
        self.connect_button.setText("關閉" if state == ConnectionState.CONNECTED else "開啟")

    def update_counters(self, rx_bytes: int, tx_bytes: int, rx_packets: int, tx_packets: int) -> None:
        self.counter_label.setText(
            f"RX {rx_bytes} B | TX {tx_bytes} B | RX 封包 {rx_packets} | TX 封包 {tx_packets}"
        )

    def update_display_mode(self, mode: DisplayMode) -> None:
        self.mode_label.setText(f"顯示：{self._DISPLAY_MODE_LABELS[mode]}")

    def update_logging_state(self, enabled: bool) -> None:
        self.logging_label.setText("日誌開啟" if enabled else "日誌關閉")
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
            "刪除模板",
            f"要刪除模板「{template_name}」嗎？",
        )
        return answer == QMessageBox.StandardButton.Yes

    def load_template_to_sender(self, template: CommandTemplate) -> None:
        self.send_text.setPlainText(template.payload)
        self._set_combo_value(self.send_mode_combo, template.mode.value)

    def apply_settings(self, state: dict) -> None:
        if geometry := state.get("geometry"):
            self.restoreGeometry(QByteArray.fromHex(geometry.encode("ascii")))
        self._set_combo_value(self.display_mode_combo, state.get("display_mode", DisplayMode.ASCII.value))
        self._set_combo_value(self.send_mode_combo, state.get("send_mode", SendMode.ASCII.value))
        self.enter_send_check.setChecked(bool(state.get("enter_send", False)))
        self.timestamp_check.setChecked(bool(state.get("show_timestamp", True)))
        self.direction_check.setChecked(bool(state.get("show_direction", True)))
        self.auto_scroll_check.setChecked(bool(state.get("auto_scroll", True)))
        newline = state.get("newline", "\n")
        newline = {"\\n": "\n", "\\r\\n": "\r\n"}.get(newline, newline)
        self._set_combo_value(self.newline_combo, newline)
        self.periodic_spin.setValue(int(state.get("periodic_interval", 1000)))

    def collect_ui_state(self) -> dict:
        return {
            "geometry": bytes(self.saveGeometry().toHex()).decode("ascii"),
            "display_mode": self.display_mode_combo.currentData() or DisplayMode.ASCII.value,
            "send_mode": self.send_mode_combo.currentData() or SendMode.ASCII.value,
            "enter_send": self.enter_send_check.isChecked(),
            "show_timestamp": self.timestamp_check.isChecked(),
            "show_direction": self.direction_check.isChecked(),
            "auto_scroll": self.auto_scroll_check.isChecked(),
            "newline": self.newline_combo.currentData() or "\n",
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
        self.send_requested.emit(
            self.send_text.toPlainText(),
            SendMode(self.send_mode_combo.currentData() or SendMode.ASCII.value),
        )

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

    def _set_advanced_visibility(self, visible: bool) -> None:
        if hasattr(self, "advanced_toggle_button"):
            self.advanced_toggle_button.blockSignals(True)
            self.advanced_toggle_button.setText("隱藏進階功能" if visible else "顯示進階功能")
            self.advanced_toggle_button.setChecked(visible)
            self.advanced_toggle_button.blockSignals(False)
        for widget in self._advanced_widgets:
            widget.setVisible(visible)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif value:
            combo.addItem(value)
            combo.setCurrentText(value)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        MainWindow._set_combo_text(combo, value)

