from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    EmployeeBucket,
    MspCategory,
    ProfileSource,
    SphereCategory,
)
from navigator.presentation.maxbot.renderers import render_measure, render_profile


def test_profile_uses_human_labels_for_fns_data() -> None:
    text = render_profile(
        BusinessProfile(
            max_user_id=1,
            company_name='ООО "ИАС ДИДЖИТАЛ"',
            inn="9715384111",
            region_code="77",
            primary_okved="62.01",
            business_form=BusinessForm.OOO,
            sphere=SphereCategory.IT_DIGITAL,
            business_stage=BusinessStage.GT3,
            employee_bucket=EmployeeBucket.SIXTEEN_TO_HUNDRED,
            msp_category=MspCategory.MICRO,
            source=ProfileSource.FNS,
        )
    )

    assert "Регион: Москва (77)" in text
    assert "Форма: юридическое лицо" in text
    assert "Основной ОКВЭД: 62.01" in text
    assert "Сфера: IT и цифровые услуги" in text
    assert "Этап бизнеса: больше 3 лет" in text
    assert "Сотрудники: 16–100" in text
    assert "Статус МСП: микропредприятие" in text
    assert "None" not in text


def test_measure_uses_human_support_level_and_reason() -> None:
    measure = type(
        "Measure",
        (),
        {
            "name": "Мера", "support_level": "federal",
            "amount_display": "Подбор программ", "benefit_detail": None,
        },
    )()

    text = render_measure(measure, ("Форма бизнеса подходит",))

    assert "Федеральный инструмент" in text
    assert "• Форма бизнеса подходит" in text
