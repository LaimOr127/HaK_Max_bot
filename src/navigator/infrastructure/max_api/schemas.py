from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

JsonDict = dict[str, Any]
TextFormat = Literal["markdown", "html"]


@dataclass(frozen=True)
class BotCommand:
    name: str
    description: str

    def to_payload(self) -> JsonDict:
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class InlineButton:
    type: str
    text: str
    payload: str | None = None
    url: str | None = None

    def to_payload(self) -> JsonDict:
        data: JsonDict = {"type": self.type, "text": self.text}
        if self.payload is not None:
            data["payload"] = self.payload
        if self.url is not None:
            data["url"] = self.url
        return data


@dataclass(frozen=True)
class NewMessageBody:
    text: str | None = None
    attachments: list[JsonDict] = field(default_factory=list)
    link: JsonDict | None = None
    notify: bool | None = None
    format: TextFormat | None = None

    def to_payload(self) -> JsonDict:
        payload: JsonDict = {}
        if self.text is not None:
            payload["text"] = self.text
        if self.attachments:
            payload["attachments"] = self.attachments
        if self.link is not None:
            payload["link"] = self.link
        if self.notify is not None:
            payload["notify"] = self.notify
        if self.format is not None:
            payload["format"] = self.format
        return payload


def inline_keyboard(rows: list[list[InlineButton]]) -> JsonDict:
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": [[button.to_payload() for button in row] for row in rows]},
    }
