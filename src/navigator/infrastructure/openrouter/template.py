from __future__ import annotations

import re

_INN_RE = re.compile(r"\b\d{10}(\d{2})?\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?:\+?\d[\s().-]*){10,}")


def scrub_pii(text: str) -> str:
    text = _INN_RE.sub("[inn]", text)
    text = _EMAIL_RE.sub("[email]", text)
    return _PHONE_RE.sub("[phone]", text)


def fallback_explanation(measure_title: str, reason: str | None = None) -> str:
    suffix = f" {reason}" if reason else ""
    return f"Эта мера может подойти по формальным признакам профиля бизнеса.{suffix}"


def build_explanation_messages(
    measure_title: str,
    profile_summary: str,
    facts: list[str],
) -> list[dict[str, str]]:
    clean_facts = "\n".join(f"- {scrub_pii(fact)}" for fact in facts[:8])
    return [
        {
            "role": "system",
            "content": (
                "Ты кратко объясняешь предпринимателю, почему мера поддержки может подойти. "
                "Не делай юридических гарантий. Не запрашивай и не повторяй ИНН, телефоны, email."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Мера: {scrub_pii(measure_title)}\n"
                f"Профиль: {scrub_pii(profile_summary)}\n"
                f"Факты:\n{clean_facts}\n"
                "Ответь в 1-2 коротких предложения."
            ),
        },
    ]
