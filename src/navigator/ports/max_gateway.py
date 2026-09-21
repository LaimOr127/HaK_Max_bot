from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Button:
    label: str
    callback: str


@dataclass(frozen=True, slots=True)
class OutgoingMessage:
    max_user_id: int
    text: str
    buttons: tuple[tuple[Button, ...], ...] = ()


class MaxGateway(Protocol):
    async def send_message(self, message: OutgoingMessage) -> None: ...
