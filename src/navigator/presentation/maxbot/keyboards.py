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
        [("Начать", "nav:start")],
        [("Как это работает?", "nav:how")],
    ]
)
WELCOME_BACK = inline_keyboard(
    [
        [("Подобрать меры", "nav:recommend")],
        [("Мой профиль", "nav:profile")],
        [("Мой чек-лист", "nav:checklist")],
        [("Проверить другой ИНН", "nav:start")],
    ]
)
RETURNING = inline_keyboard(
    [
        [("Показать меры ещё раз", "nav:recommend")],
        [("Мой чек-лист", "nav:checklist")],
        [("Изменить профиль", "profile:edit")],
        [("Помощь", "nav:help")],
    ]
)
INN = inline_keyboard([[("Заполнить вручную", "inn:manual")]])
INN_INVALID = INN
INN_ERROR = inline_keyboard(
    [
        [("Ввести заново", "inn:retry")],
        [("Заполнить вручную", "inn:manual")],
    ]
)
INN_UNAVAILABLE = inline_keyboard(
    [[("Повторить", "inn:retry")], [("Заполнить вручную", "inn:manual")]]
)
BUSINESS_FORM = inline_keyboard(
    [
        [("ИП", "business_form:ip"), ("ООО", "business_form:ooo")],
        [("Самозанятый", "business_form:self_employed")],
    ]
)
SPHERE = inline_keyboard(
    [
        [("Общепит", "sphere:food"), ("Розничная торговля", "sphere:retail")],
        [
            ("Бытовые услуги", "sphere:household"),
            ("Деловые услуги", "sphere:professional"),
        ],
        [("IT и цифровые услуги", "sphere:it"), ("Производство", "sphere:manufacturing")],
        [("Строительство и ремонт", "sphere:construction")],
        [("Красота", "sphere:beauty"), ("Здоровье и медицина", "sphere:health")],
        [("Образование", "sphere:education"), ("Туризм", "sphere:tourism")],
        [("Транспорт и логистика", "sphere:transport"), ("Прочее", "sphere:other")],
        [("Назад", "profile:back")],
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
PROFILE_SAVED = inline_keyboard(
    [[("Подобрать меры", "nav:recommend")], [("Изменить данные", "profile:edit")]]
)
RESET = inline_keyboard(
    [
        [("Да, сбросить", "reset:confirm")],
        [("Отмена", "reset:cancel")],
    ]
)
ZERO_RESULTS = inline_keyboard(
    [
        [("Уточнить детали", "profile:edit")],
        [("Сообщить, чего не хватает", "nav:zero_feedback")],
    ]
)
INVESTOR = inline_keyboard(
    [
        [("Да, интересно", "investor:yes")],
        [("Не сейчас", "investor:no")],
    ]
)


def measure(measure_id: str, *, in_checklist: bool = False) -> list[dict[str, object]]:
    return inline_keyboard(
        [
            [("Подробнее", f"measure:details:{measure_id}")],
            [
                ("✓ В чек-листе", f"measure:remove_ask:{measure_id}")
                if in_checklist else ("Добавить в чек-лист", f"measure:add:{measure_id}")
            ],
            [("Мера не подходит", f"measure:feedback:{measure_id}")],
        ]
    )


def compare(web_app: str, first_id: str, second_id: str) -> list[dict[str, object]]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [[{
                    "type": "open_app",
                    "text": "Сравнить",
                    "web_app": web_app,
                    "payload": f"compare_{first_id}_{second_id}",
                }], [{"type": "callback", "text": "Не нужно", "payload": "nav:skip_compare"}]]
            },
        }
    ]


def home(web_app: str) -> list[dict[str, object]]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [[{
                    "type": "open_app",
                    "text": "Открыть навигатор",
                    "web_app": web_app,
                    "payload": "home",
                }], [{"type": "callback", "text": "Начать", "payload": "nav:start"}],
                [{"type": "callback", "text": "Как это работает?", "payload": "nav:how"}]]
            },
        }
    ]


def document(document_id: str, is_done: bool) -> list[dict[str, object]]:
    label = "Отметить неготовым" if is_done else "Отметить готовым"
    return inline_keyboard([[(label, f"document:toggle:{document_id}")]])
