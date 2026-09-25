from datetime import date
from decimal import Decimal

from navigator.infrastructure.data.import_measures import load_csv, parse_rows
from navigator.infrastructure.data.seed import _expand_okved, repo_data_dir


def valid_row(**changes: str) -> dict[str, str]:
    row = {
        "external_code": "TEST-1",
        "name": "Test measure",
        "support_level": "federal",
        "regions": "77|50",
        "spheres": "retail|it_digital",
        "business_forms": "ip|ooo",
        "business_stages": "new|lt1",
        "msp_categories": "micro|small",
        "employee_min": "1",
        "employee_max": "15",
        "amount_display": "До 100 ₽",
        "amount_min_rub": "10",
        "amount_max_rub": "100",
        "benefit_detail": "grant",
        "what_is_it": "Subsidy",
        "who_can_receive": "MSP",
        "documents": "Application|Budget",
        "where_to_apply": "Portal",
        "review_days": "30",
        "valid_from": "2026-01-01",
        "application_deadline": "2026-12-31",
        "source_name": "Source",
        "source_url": "https://example.com/measure",
        "source_checked_at": "2026-09-01",
        "is_active": "true",
        "priority": "10",
    }
    row.update(changes)
    return row


def test_parse_valid_measure_row() -> None:
    rows, errors = parse_rows([valid_row()])

    assert errors == []
    assert rows[0].external_code == "TEST-1"
    assert rows[0].regions == ("77", "50")
    assert rows[0].amount_max_rub == Decimal("100")
    assert rows[0].source_checked_at == date(2026, 9, 1)


def test_parse_reports_validation_errors_with_row_and_column() -> None:
    _, errors = parse_rows(
        [
            valid_row(
                spheres="unknown",
                employee_min="20",
                employee_max="2",
                source_url="file:///tmp/bad",
                application_deadline="2025-12-31",
            ),
            valid_row(external_code="TEST-1"),
        ]
    )

    messages = {str(error) for error in errors}
    assert "row 2, column spheres: unknown value 'unknown'" in messages
    assert "row 2, column employee_min: must be <= employee_max" in messages
    assert "row 2, column source_url: invalid URL 'file:///tmp/bad'" in messages
    assert "row 2, column application_deadline: must be >= valid_from" in messages
    assert "row 3, column external_code: duplicate value in file" in messages


def test_measure_catalogs_load() -> None:
    rows, errors = load_csv(repo_data_dir() / "measures.example.csv")

    assert errors == []
    assert {row.external_code for row in rows} == {f"MVP-{index:02d}" for index in range(1, 30)}
    assert {sphere for row in rows for sphere in row.spheres} >= {
        "professional",
        "health",
        "tourism",
    }
    assert all(row.source_name.startswith("Синтетические данные (MVP)") for row in rows)

    current_rows, current_errors = load_csv(repo_data_dir() / "measures.current.csv")
    assert current_errors == []
    assert {row.external_code for row in current_rows} == {"MSP-RF-CATALOG", "MOS-SUPPLIER-PORTAL"}


def test_okved_ranges_expand_to_two_digit_classes() -> None:
    assert _expand_okved("58-63") == ("58", "59", "60", "61", "62", "63")
    assert _expand_okved("7") == ("07",)
