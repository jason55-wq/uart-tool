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
        self.setWindowTitle("Command Template")
        self._template = template

        self.name_edit = QLineEdit(template.name if template else "")
        self.category_edit = QLineEdit(template.category if template else "General")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([SendMode.ASCII.value, SendMode.HEX.value])
        if template:
            self.mode_combo.setCurrentText(template.mode.value)
        self.payload_edit = QPlainTextEdit(template.payload if template else "")
        self.payload_edit.setPlaceholderText("Enter ASCII text or HEX bytes")

        form = QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Category", self.category_edit)
        form.addRow("Mode", self.mode_combo)
        form.addRow("Payload", self.payload_edit)

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
            QMessageBox.warning(self, "Template", "Template name is required.")
            return
        if not self.payload_edit.toPlainText().strip():
            QMessageBox.warning(self, "Template", "Payload is required.")
            return
        super().accept()

    def build_template(self) -> CommandTemplate:
        template_id = self._template.template_id if self._template else None
        kwargs = {
            "name": self.name_edit.text().strip(),
            "category": self.category_edit.text().strip() or "General",
            "payload": self.payload_edit.toPlainText(),
            "mode": SendMode(self.mode_combo.currentText()),
        }
        if template_id:
            kwargs["template_id"] = template_id
        return CommandTemplate(**kwargs)

