from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any


_PROFILE_LABELS = {
    "business_form": {"ip": "ИП", "ooo": "ООО", "self_employed": "самозанятый"},
    "sphere": {
        "foodservice": "общепит",
        "retail": "розничная торговля",
        "household_services": "бытовые услуги",
        "it_digital": "IT и цифровые услуги",
        "manufacturing": "производство",
        "construction_repair": "строительство и ремонт",
        "beauty_health": "красота и здоровье",
        "education": "образование",
        "transport_logistics": "транспорт и логистика",
        "other": "прочее",
    },
    "business_stage": {"new": "только открылись", "lt1": "до 1 года", "1_3": "1–3 года", "gt3": "больше 3 лет"},
    "employee_bucket": {"1": "1", "2_15": "2–15", "16_100": "16–100", "100_plus": "больше 100"},
    "msp_category": {"micro": "микропредприятие", "small": "малое предприятие", "medium": "среднее предприятие"},
}
_REGION_LABELS = {"77": "Москва (77)"}


def _profile_value(profile: Any, field: str, default: str) -> str:
    value = getattr(profile, field, None)
    if value is None:
        return default
    raw = str(getattr(value, "value", value))
    return _PROFILE_LABELS.get(field, {}).get(raw, raw)


def render_profile(profile: Any) -> str:
    source = (
        "ФНС" if str(getattr(profile, "source", "")).lower().endswith("fns") else "введено вручную"
    )
    sphere = _profile_value(profile, "sphere", "уточним далее")
    if sphere == "уточним далее":
        sphere = _profile_value(profile, "sphere_code", sphere)
    if sphere == "уточним далее":
        sphere = _profile_value(profile, "sphere_category_id", sphere)
    region = getattr(profile, "region_code", None)
    region = _REGION_LABELS.get(str(region), str(region)) if region else "не указан"
    okved = getattr(profile, "primary_okved", None)
    okved_line = f"Основной ОКВЭД: {okved}\n" if okved else ""
    return (
        "Проверьте профиль:\n\n"
        f"Компания: {getattr(profile, 'company_name', None) or 'не указано'}\n"
        f"ИНН: {getattr(profile, 'inn', None) or 'не указан'}\n"
        f"Регион: {region}\n"
        f"Форма: {_profile_value(profile, 'business_form', 'уточним далее')}\n"
        f"{okved_line}"
        f"Сфера: {sphere}\n"
        f"Этап бизнеса: {_profile_value(profile, 'business_stage', 'уточним далее')}\n"
        f"Сотрудники: {_profile_value(profile, 'employee_bucket', 'уточним далее')}\n"
        f"Статус МСП: {_profile_value(profile, 'msp_category', 'нет данных')}\n"
        f"Источник: {source}\n\n"
        "Всё верно, и вы подтверждаете, что представляете этот бизнес?\n\n"
        "Данные из открытых источников носят справочный характер. "
        "Сервис не проверяет ваши полномочия представлять компанию."
    )


def render_measure(measure: Any, reasons: Iterable[str]) -> str:
    level = {"federal": "Федеральный инструмент", "regional": "Региональный инструмент"}.get(
        str(getattr(measure, "support_level", "")), "Инструмент поддержки"
    )
    bullets = "\n".join(f"• {reason}" for reason in list(reasons)[:3])
    detail = getattr(measure, "benefit_detail", None)
    detail_text = f"\n{detail}" if detail else ""
    return (
        f"{measure.name}\n\n{level}\n{measure.amount_display}"
        f"{detail_text}\n\nПочему может подойти:\n{bullets or '• Условия сверяются в первоисточнике.'}"
    )


def render_measure_details(measure: Any, documents: Iterable[Any]) -> str:
    docs = "\n".join(
        f"{index}. {getattr(doc, 'title', doc)}" for index, doc in enumerate(documents, 1)
    )
    deadline = getattr(measure, "application_deadline", None)
    deadline_text = (
        deadline.strftime("%d.%m.%Y") if isinstance(deadline, date) else "уточните в первоисточнике"
    )
    return (
        f"{measure.name}\n\nЧто это\n{measure.what_is_it}\n\n"
        f"Кто может получить\n{measure.who_can_receive}\n\n"
        f"Поддержка\n{measure.amount_display}\n{getattr(measure, 'benefit_detail', '') or ''}\n\n"
        f"Документы\n{docs}\n\nКуда подавать\n{measure.where_to_apply}\n\n"
        f"Срок рассмотрения\n{getattr(measure, 'review_days', None) or 'зависит от программы'}\n\n"
        f"Срок подачи\n{deadline_text}\n\nИсточник\n{measure.source_name}\n{measure.source_url}\n\n"
        "По данным профиля мера соответствует указанным структурированным критериям. "
        "Перед подачей проверьте актуальные условия в первоисточнике."
    )
