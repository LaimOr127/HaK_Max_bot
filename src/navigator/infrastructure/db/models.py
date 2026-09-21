from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from navigator.infrastructure.db.base import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_last_seen_at", "last_seen_at"),)

    max_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    investor_prompt_state: Mapped[str] = mapped_column(
        String(32), default="not_shown", nullable=False
    )


class ConversationState(Base):
    __tablename__ = "conversation_states"

    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SphereCategory(Base):
    __tablename__ = "sphere_categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class OkvedMapping(Base):
    __tablename__ = "okved_mappings"

    okved_class: Mapped[str] = mapped_column(String(2), primary_key=True)
    sphere_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sphere_categories.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)


class Region(Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )


class CompanyProfile(TimestampMixin, Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        Index("ix_company_profiles_inn", "inn"),
        UniqueConstraint("max_user_id", name="uq_company_profiles_max_user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), nullable=False
    )
    inn: Mapped[str | None] = mapped_column(String(12))
    company_name: Mapped[str | None] = mapped_column(String(512))
    region_code: Mapped[str | None] = mapped_column(String(16), ForeignKey("regions.code"))
    primary_okved: Mapped[str | None] = mapped_column(String(16))
    sphere_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sphere_categories.id")
    )
    business_stage: Mapped[str | None] = mapped_column(String(32))
    business_form: Mapped[str | None] = mapped_column(String(16))
    employee_bucket: Mapped[str | None] = mapped_column(String(32))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    msp_category: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fns_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Measure(TimestampMixin, Base):
    __tablename__ = "measures"
    __table_args__ = (
        Index("ix_measures_is_active", "is_active"),
        Index("ix_measures_application_deadline", "application_deadline"),
        Index("ix_measures_priority", "priority"),
        Index("ix_measures_amount_max_rub", "amount_max_rub"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    external_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    support_level: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_display: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_min_rub: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount_max_rub: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    benefit_detail: Mapped[str | None] = mapped_column(Text)
    what_is_it: Mapped[str] = mapped_column(Text, nullable=False)
    who_can_receive: Mapped[str] = mapped_column(Text, nullable=False)
    where_to_apply: Mapped[str] = mapped_column(Text, nullable=False)
    review_days: Mapped[int | None] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_at: Mapped[date] = mapped_column(Date, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    employee_min: Mapped[int | None] = mapped_column(Integer)
    employee_max: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)


class MeasureRegion(Base):
    __tablename__ = "measure_regions"
    __table_args__ = (UniqueConstraint("measure_id", "region_code", name="uq_measure_regions"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    region_code: Mapped[str] = mapped_column(String(16), ForeignKey("regions.code"), nullable=False)


class MeasureSphere(Base):
    __tablename__ = "measure_spheres"
    __table_args__ = (
        UniqueConstraint("measure_id", "sphere_category_id", name="uq_measure_spheres"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    sphere_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sphere_categories.id"), nullable=False
    )


class MeasureBusinessForm(Base):
    __tablename__ = "measure_business_forms"
    __table_args__ = (UniqueConstraint("measure_id", "business_form", name="uq_measure_forms"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    business_form: Mapped[str] = mapped_column(String(16), nullable=False)


class MeasureBusinessStage(Base):
    __tablename__ = "measure_business_stages"
    __table_args__ = (UniqueConstraint("measure_id", "business_stage", name="uq_measure_stages"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    business_stage: Mapped[str] = mapped_column(String(32), nullable=False)


class MeasureMspCategory(Base):
    __tablename__ = "measure_msp_categories"
    __table_args__ = (UniqueConstraint("measure_id", "msp_category", name="uq_measure_msp"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    msp_category: Mapped[str] = mapped_column(String(32), nullable=False)


class MeasureDocument(Base):
    __tablename__ = "measure_documents"
    __table_args__ = (UniqueConstraint("measure_id", "code", name="uq_measure_documents_code"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)


class UserMeasureChecklist(Base):
    __tablename__ = "user_measure_checklists"
    __table_args__ = (
        UniqueConstraint("max_user_id", "measure_id", name="uq_user_measure_checklists"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), nullable=False
    )
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChecklistDocumentState(Base):
    __tablename__ = "checklist_document_states"
    __table_args__ = (
        UniqueConstraint(
            "checklist_id", "measure_document_id", name="uq_checklist_document_states"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_measure_checklists.id", ondelete="CASCADE"),
        nullable=False,
    )
    measure_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measure_documents.id", ondelete="CASCADE"), nullable=False
    )
    is_done: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sphere_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sphere_categories.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class MeasureFeedback(Base):
    __tablename__ = "measure_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), nullable=False
    )
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InvestorLead(Base):
    __tablename__ = "investor_leads"

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), primary_key=True
    )
    checklist_add_count: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_type_created", "event_type", "created_at"),
        Index("ix_analytics_events_user_created", "max_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    measure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="SET NULL")
    )
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReminderDelivery(Base):
    __tablename__ = "reminder_deliveries"
    __table_args__ = (
        UniqueConstraint("max_user_id", "measure_id", "days_before", name="uq_reminder_deliveries"),
        CheckConstraint("days_before > 0", name="ck_reminder_deliveries_days_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    max_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.max_user_id", ondelete="CASCADE"), nullable=False
    )
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False
    )
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
