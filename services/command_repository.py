from __future__ import annotations

import json
from typing import Optional

from models.command_template import CommandTemplate
from utils.paths import app_data_dir


class CommandRepository:
    """JSON-backed repository for reusable command templates."""

    def __init__(self) -> None:
        self._path = app_data_dir() / "command_templates.json"
        self._templates = self._load()

    def list_templates(self) -> list[CommandTemplate]:
        return list(self._templates)

    def get_template(self, template_id: str) -> Optional[CommandTemplate]:
        return next((item for item in self._templates if item.template_id == template_id), None)

    def add_template(self, template: CommandTemplate) -> None:
        self._templates.append(template)
        self._save()

    def update_template(self, updated: CommandTemplate) -> None:
        for index, current in enumerate(self._templates):
            if current.template_id == updated.template_id:
                self._templates[index] = updated
                self._save()
                return

    def delete_template(self, template_id: str) -> None:
        self._templates = [item for item in self._templates if item.template_id != template_id]
        self._save()

    def _load(self) -> list[CommandTemplate]:
        if not self._path.exists():
            defaults = [
                CommandTemplate(name="AT", payload="AT\r\n"),
                CommandTemplate(name="AT+GMR", payload="AT+GMR\r\n"),
                CommandTemplate(name="AT+RST", payload="AT+RST\r\n"),
            ]
            self._path.write_text(
                json.dumps([item.to_dict() for item in defaults], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return defaults

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return [CommandTemplate.from_dict(item) for item in payload]

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([item.to_dict() for item in self._templates], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

