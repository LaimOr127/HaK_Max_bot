from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any


def render_profile(profile: Any) -> str:
    source = (
        "ФНС" if str(getattr(profile, "source", "")).lower().endswith("fns") else "введено вручную"
    )
    sphere = getattr(profile, "sphere", None)
    sphere = sphere or getattr(profile, "sphere_code", None)
    sphere = sphere or getattr(profile, "sphere_category_id", "не указана")
    return (
        "Проверьте профиль:\n\n"
        f"Компания: {getattr(profile, 'company_name', None) or 'не указано'}\n"
        f"ИНН: {getattr(profile, 'inn', None) or 'не указан'}\n"
        f"Регион: {getattr(profile, 'region_code', 'не указан')}\n"
        f"Форма: {getattr(profile, 'business_form', 'не указана')}\n"
        f"Сфера: {sphere}\n"
        f"Этап бизнеса: {getattr(profile, 'business_stage', 'не указан')}\n"
        f"Сотрудники: {getattr(profile, 'employee_bucket', 'не указаны')}\n"
        f"Статус МСП: {getattr(profile, 'msp_category', None) or 'нет данных'}\n"
        f"Источник: {source}\n\n"
        "Всё верно, и вы подтверждаете, что представляете этот бизнес?\n\n"
        "Данные из открытых источников носят справочный характер. "
        "Сервис не проверяет ваши полномочия представлять компанию."
    )


def render_measure(measure: Any, reasons: Iterable[str]) -> str:
    level = getattr(measure, "support_level", "")
    bullets = "\n".join(f"• {reason}" for reason in list(reasons)[:3])
    detail = getattr(measure, "benefit_detail", None)
    detail_text = f"\n{detail}" if detail else ""
    return (
        f"{measure.name}\n\n{level}\n{measure.amount_display}"
        f"{detail_text}\n\nПочему может подойти:\n{bullets}"
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
