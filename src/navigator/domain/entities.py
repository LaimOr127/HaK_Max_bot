from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .enums import (
    BusinessForm,
    BusinessStage,
    EmployeeBucket,
    FeedbackType,
    MspCategory,
    ProfileSource,
    SphereCategory,
    SupportLevel,
)


@dataclass(frozen=True, slots=True)
class BusinessProfile:
    max_user_id: int
    region_code: str | None = None
    sphere: SphereCategory | None = None
    business_stage: BusinessStage | None = None
    business_form: BusinessForm | None = None
    employee_bucket: EmployeeBucket | None = None
    inn: str | None = None
    company_name: str | None = None
    primary_okved: str | None = None
    msp_category: MspCategory | None = None
    employee_count: int | None = None
    source: ProfileSource = ProfileSource.MANUAL
    consent_at: datetime | None = None
    fns_checked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MeasureDocument:
    id: UUID
    measure_id: UUID
    code: str
    title: str
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class Measure:
    id: UUID
    external_code: str
    name: str
    support_level: SupportLevel
    amount_display: str
    what_is_it: str
    who_can_receive: str
    where_to_apply: str
    source_name: str
    source_url: str
    source_checked_at: date
    amount_min_rub: Decimal | None = None
    amount_max_rub: Decimal | None = None
    benefit_detail: str | None = None
    review_days: int | None = None
    valid_from: date | None = None
    application_deadline: date | None = None
    employee_min: int | None = None
    employee_max: int | None = None
    is_active: bool = True
    is_demo: bool = False
    priority: int = 0
    regions: frozenset[str] = field(default_factory=frozenset)
    spheres: frozenset[SphereCategory] = field(default_factory=frozenset)
    business_forms: frozenset[BusinessForm] = field(default_factory=frozenset)
    business_stages: frozenset[BusinessStage] = field(default_factory=frozenset)
    msp_categories: frozenset[MspCategory] = field(default_factory=frozenset)
    documents: tuple[MeasureDocument, ...] = ()


@dataclass(frozen=True, slots=True)
class ChecklistDocumentState:
    id: UUID
    measure_document_id: UUID
    title: str
    is_done: bool = False
    done_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UserMeasureChecklist:
    id: UUID
    max_user_id: int
    measure_id: UUID
    measure_name: str
    added_at: datetime
    documents: tuple[ChecklistDocumentState, ...] = ()


@dataclass(frozen=True, slots=True)
class Feedback:
    max_user_id: int
    measure_id: UUID
    feedback_type: FeedbackType
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class InvestorLead:
    max_user_id: int
    name: str
    contact: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.contact.strip():
            raise ValueError("investor lead name and contact are required")
