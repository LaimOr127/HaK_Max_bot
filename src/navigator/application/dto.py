from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from navigator.domain.entities import BusinessProfile, UserMeasureChecklist
from navigator.domain.enums import FeedbackType, MatchStatus


@dataclass(frozen=True, slots=True)
class ProfileInput:
    max_user_id: int
    region_code: str
    business_form: str
    sphere: str
    business_stage: str
    employee_bucket: str
    inn: str | None = None
    company_name: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationDTO:
    measure_id: UUID
    name: str
    amount_display: str
    support_level: str
    status: MatchStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MeasureDetailsDTO:
    measure_id: UUID
    name: str
    what_is_it: str
    who_can_receive: str
    amount_display: str
    benefit_detail: str | None
    documents: tuple[str, ...]
    where_to_apply: str
    review_days: int | None
    application_deadline: date | None
    source_name: str
    source_url: str
    source_checked_at: date


@dataclass(frozen=True, slots=True)
class ChecklistDTO:
    checklists: tuple[UserMeasureChecklist, ...]


@dataclass(frozen=True, slots=True)
class FeedbackInput:
    max_user_id: int
    measure_id: UUID
    feedback_type: FeedbackType
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class InvestorLeadInput:
    max_user_id: int
    name: str
    contact: str


@dataclass(frozen=True, slots=True)
class ProfileConfirmation:
    profile: BusinessProfile
    recommendations: tuple[RecommendationDTO, ...]
