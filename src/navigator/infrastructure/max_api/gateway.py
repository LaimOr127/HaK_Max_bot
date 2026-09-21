from __future__ import annotations

from navigator.infrastructure.max_api.client import MaxApiClient
from navigator.infrastructure.max_api.schemas import InlineButton, NewMessageBody, inline_keyboard
from navigator.ports.max_gateway import OutgoingMessage


class MaxApiGateway:
    def __init__(self, client: MaxApiClient) -> None:
        self._client = client

    async def send_message(self, message: OutgoingMessage) -> None:
        attachments = []
        if message.buttons:
            attachments.append(
                inline_keyboard(
                    [
                        [
                            InlineButton("callback", button.label, payload=button.callback)
                            for button in row
                        ]
                        for row in message.buttons
                    ]
                )
            )
        await self._client.send_message(
            NewMessageBody(text=message.text, attachments=attachments),
            user_id=message.max_user_id,
        )
