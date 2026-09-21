from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


class InvalidCallback(ValueError):
    """Raised when a callback payload does not match the public callback contract."""


@dataclass(frozen=True, slots=True)
class Callback:
    action: str
    values: tuple[str, ...] = ()

    def uuid(self, position: int = 0) -> UUID:
        try:
            return UUID(self.values[position])
        except (IndexError, ValueError) as exc:
            raise InvalidCallback("callback contains an invalid UUID") from exc


_EXACT = {
    "nav:start",
    "nav:how",
    "nav:help",
    "nav:profile",
    "nav:checklist",
    "inn:manual",
    "inn:retry",
    "profile:confirm",
    "profile:edit",
    "profile:edit_inn",
    "profile:edit_manual",
    "reset:confirm",
    "reset:cancel",
    "investor:yes",
    "investor:no",
}
_ENUMS = {
    "employees": {"1", "2_15", "16_100", "100_plus"},
    "business_form": {"ip", "ooo", "self_employed"},
    "sphere": {
        "foodservice",
        "retail",
        "household_services",
        "it_digital",
        "manufacturing",
        "construction_repair",
        "beauty_health",
        "education",
        "transport_logistics",
        "other",
    },
    "stage": {"new", "lt1", "1_3", "gt3"},
}
_UUID_ACTIONS = {
    "measure:details",
    "measure:add",
    "measure:remove_ask",
    "measure:remove_confirm",
    "measure:feedback",
    "feedback:not_eligible",
    "feedback:outdated",
    "feedback:other",
    "document:toggle",
}


def parse_callback(payload: str) -> Callback:
    if payload in _EXACT:
        action, value = payload.split(":", 1)
        return Callback(f"{action}:{value}")

    parts = payload.split(":")
    if len(parts) == 2 and parts[0] in _ENUMS and parts[1] in _ENUMS[parts[0]]:
        return Callback(parts[0], (parts[1],))

    action = ":".join(parts[:2])
    if len(parts) == 3 and action in _UUID_ACTIONS:
        callback = Callback(action, (parts[2],))
        callback.uuid()
        return callback

    if len(parts) == 3 and parts[0] == "compare":
        callback = Callback("compare", (parts[1], parts[2]))
        callback.uuid(0)
        callback.uuid(1)
        return callback

    raise InvalidCallback("unknown callback")
