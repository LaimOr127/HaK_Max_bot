from __future__ import annotations

from collections.abc import Iterable

Button = tuple[str, str]


def inline_keyboard(rows: Iterable[Iterable[Button]]) -> list[dict[str, object]]:
    buttons = [
        [{"type": "callback", "text": label, "payload": payload} for label, payload in row]
        for row in rows
    ]
    return [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]


WELCOME = inline_keyboard(
    [
        [("Начать подбор", "nav:start")],
        [("Как это работает?", "nav:how")],
    ]
)
WELCOME_BACK = inline_keyboard(
    [
        [("Подобрать меры", "nav:recommend")],
        [("Мой профиль", "nav:profile")],
        [("Мой чек-лист", "nav:checklist")],
        [("Начать сначала", "nav:start")],
    ]
)
INN = inline_keyboard([[("Заполнить вручную", "inn:manual")]])
INN_ERROR = inline_keyboard(
    [
        [("Ввести снова", "inn:retry")],
        [("Заполнить вручную", "inn:manual")],
    ]
)
BUSINESS_FORM = inline_keyboard(
    [
        [("ИП", "business_form:ip"), ("ООО", "business_form:ooo")],
        [("Самозанятый", "business_form:self_employed")],
    ]
)
SPHERE = inline_keyboard(
    [
        [("Общепит", "sphere:foodservice"), ("Розничная торговля", "sphere:retail")],
        [
            ("Бытовые услуги", "sphere:household_services"),
            ("IT и цифровые услуги", "sphere:it_digital"),
        ],
        [
            ("Производство", "sphere:manufacturing"),
            ("Строительство и ремонт", "sphere:construction_repair"),
        ],
        [("Красота и здоровье", "sphere:beauty_health"), ("Образование", "sphere:education")],
        [("Транспорт и логистика", "sphere:transport_logistics"), ("Прочее", "sphere:other")],
    ]
)
STAGE = inline_keyboard(
    [
        [("Только открылись", "stage:new"), ("До 1 года", "stage:lt1")],
        [("1–3 года", "stage:1_3"), ("Больше 3 лет", "stage:gt3")],
    ]
)
EMPLOYEES = inline_keyboard(
    [
        [("1", "employees:1"), ("2–15", "employees:2_15")],
        [("16–100", "employees:16_100"), ("Больше 100", "employees:100_plus")],
    ]
)
CONFIRM = inline_keyboard(
    [
        [("Да, всё верно", "profile:confirm")],
        [("Изменить данные", "profile:edit")],
    ]
)
RESET = inline_keyboard(
    [
        [("Да, удалить", "reset:confirm")],
        [("Отмена", "reset:cancel")],
    ]
)
INVESTOR = inline_keyboard(
    [
        [("Да, интересно", "investor:yes")],
        [("Не сейчас", "investor:no")],
    ]
)


def measure(measure_id: str) -> list[dict[str, object]]:
    return inline_keyboard(
        [
            [("Подробнее", f"measure:details:{measure_id}")],
            [("В чек-лист", f"measure:add:{measure_id}")],
            [("Мера не подходит", f"measure:feedback:{measure_id}")],
        ]
    )


def document(document_id: str, is_done: bool) -> list[dict[str, object]]:
    label = "Отметить неготовым" if is_done else "Отметить готовым"
    return inline_keyboard([[(label, f"document:toggle:{document_id}")]])
