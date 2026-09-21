from __future__ import annotations

from navigator.ports.clock import Clock
from navigator.ports.max_gateway import Button, MaxGateway, OutgoingMessage
from navigator.ports.repositories import ReminderRepository


class ReminderService:
    def __init__(self, reminders: ReminderRepository, gateway: MaxGateway, clock: Clock) -> None:
        self._reminders = reminders
        self._gateway = gateway
        self._clock = clock

    async def send_due(self, days_before: int) -> int:
        sent = 0
        for checklist in await self._reminders.due_checklists(self._clock.today(), days_before):
            if not await self._reminders.mark_sent(
                checklist.max_user_id, checklist.measure_id, days_before
            ):
                continue
            await self._gateway.send_message(
                OutgoingMessage(
                    max_user_id=checklist.max_user_id,
                    text=(
                        f"Напоминание: до срока подачи по мере "
                        f"«{checklist.measure_name}» осталось {days_before} дн.\n\n"
                        "Проверьте, все ли документы готовы."
                    ),
                    buttons=((Button("Открыть чек-лист", "nav:checklist"),),),
                )
            )
            sent += 1
        return sent
