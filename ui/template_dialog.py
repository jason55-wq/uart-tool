from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from models.command_template import CommandTemplate
from models.enums import SendMode


class TemplateEditDialog(QDialog):
    """Dialog for creating or editing command templates."""

    def __init__(self, parent=None, template: Optional[CommandTemplate] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("命令模板")
        self._template = template

        self.name_edit = QLineEdit(template.name if template else "")
        self.category_edit = QLineEdit(template.category if template else "一般")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("ASCII 文字", SendMode.ASCII.value)
        self.mode_combo.addItem("十六進位", SendMode.HEX.value)
        if template:
            self._set_combo_value(self.mode_combo, template.mode.value)
        self.payload_edit = QPlainTextEdit(template.payload if template else "")
        self.payload_edit.setPlaceholderText("請輸入 ASCII 文字或 HEX 位元組")

        form = QFormLayout()
        form.addRow("名稱", self.name_edit)
        form.addRow("分類", self.category_edit)
        form.addRow("模式", self.mode_combo)
        form.addRow("內容", self.payload_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(420, 260)

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "模板", "必須輸入模板名稱。")
            return
        if not self.payload_edit.toPlainText().strip():
            QMessageBox.warning(self, "模板", "必須輸入內容。")
            return
        super().accept()

    def build_template(self) -> CommandTemplate:
        template_id = self._template.template_id if self._template else None
        kwargs = {
            "name": self.name_edit.text().strip(),
            "category": self.category_edit.text().strip() or "一般",
            "payload": self.payload_edit.toPlainText(),
            "mode": SendMode(self.mode_combo.currentData() or SendMode.ASCII.value),
        }
        if template_id:
            kwargs["template_id"] = template_id
        return CommandTemplate(**kwargs)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

