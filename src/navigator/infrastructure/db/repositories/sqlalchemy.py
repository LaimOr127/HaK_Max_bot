from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from navigator.domain import entities as domain
from navigator.domain.enums import (
    AnalyticsEventType,
    BusinessForm,
    BusinessStage,
    ConversationState,
    EmployeeBucket,
    InvestorPromptState,
    MspCategory,
    ProfileSource,
    SphereCategory,
    SupportLevel,
)
from navigator.domain.errors import ChecklistNotFound
from navigator.infrastructure.db import models as db


class SqlAlchemyProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user(self, max_user_id: int) -> domain.BusinessProfile | None:
        row = (
            await self._session.execute(
                select(db.CompanyProfile, db.SphereCategory.code)
                .outerjoin(
                    db.SphereCategory,
                    db.CompanyProfile.sphere_category_id == db.SphereCategory.id,
                )
                .where(db.CompanyProfile.max_user_id == max_user_id)
            )
        ).first()
        if row is None:
            return None
        profile, sphere_code = row
        return domain.BusinessProfile(
            max_user_id=profile.max_user_id,
            region_code=profile.region_code,
            sphere=SphereCategory(sphere_code) if sphere_code else None,
            business_stage=(
                BusinessStage(profile.business_stage) if profile.business_stage else None
            ),
            business_form=BusinessForm(profile.business_form) if profile.business_form else None,
            employee_bucket=(
                EmployeeBucket(profile.employee_bucket) if profile.employee_bucket else None
            ),
            inn=profile.inn,
            company_name=profile.company_name,
            primary_okved=profile.primary_okved,
            msp_category=MspCategory(profile.msp_category) if profile.msp_category else None,
            employee_count=profile.employee_count,
            source=ProfileSource(profile.source),
            consent_at=profile.consent_at,
            fns_checked_at=profile.fns_checked_at,
        )

    async def save(self, profile: domain.BusinessProfile) -> None:
        await _ensure_user(self._session, profile.max_user_id)
        await _ensure_region(self._session, profile.region_code)
        sphere_id = await _sphere_id(self._session, profile.sphere)
        values = {
            "max_user_id": profile.max_user_id,
            "inn": profile.inn,
            "company_name": profile.company_name,
            "region_code": profile.region_code,
            "primary_okved": profile.primary_okved,
            "sphere_category_id": sphere_id,
            "business_stage": _value(profile.business_stage),
            "business_form": _value(profile.business_form),
            "employee_bucket": _value(profile.employee_bucket),
            "employee_count": profile.employee_count,
            "msp_category": _value(profile.msp_category),
            "source": profile.source.value,
            "consent_at": profile.consent_at,
            "fns_checked_at": profile.fns_checked_at,
        }
        stmt = (
            insert(db.CompanyProfile)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_update(
                constraint="uq_company_profiles_max_user_id",
                set_={**values, "updated_at": func.now()},
            )
        )
        await self._session.execute(stmt)

    async def delete_by_user(self, max_user_id: int) -> None:
        await self._session.execute(delete(db.User).where(db.User.max_user_id == max_user_id))


class SqlAlchemyConversationStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_state(
        self, max_user_id: int
    ) -> tuple[ConversationState, dict[str, object]] | None:
        state = await self._session.get(db.ConversationState, max_user_id)
        if state is None:
            return None
        return ConversationState(state.state), dict(state.context)

    async def set_state(
        self,
        max_user_id: int,
        state: ConversationState,
        context: dict[str, object] | None = None,
    ) -> None:
        await _ensure_user(self._session, max_user_id)
        values = {"state": state.value, "context": context or {}, "updated_at": func.now()}
        stmt = (
            insert(db.ConversationState)
            .values(max_user_id=max_user_id, **values)
            .on_conflict_do_update(index_elements=["max_user_id"], set_=values)
        )
        await self._session.execute(stmt)


class SqlAlchemyMeasureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_candidates(self, today: date) -> list[domain.Measure]:
        rows = (
            await self._session.execute(
                select(db.Measure)
                .where(db.Measure.is_active.is_(True))
                .where(
                    (db.Measure.valid_from.is_(None)) | (db.Measure.valid_from <= today),
                    (db.Measure.application_deadline.is_(None))
                    | (db.Measure.application_deadline >= today),
                )
                .order_by(db.Measure.priority.desc(), db.Measure.name)
            )
        ).scalars()
        return [await _measure_to_domain(self._session, row) for row in rows]

    async def get(self, measure_id: UUID) -> domain.Measure | None:
        measure = await self._session.get(db.Measure, measure_id)
        if measure is None:
            return None
        return await _measure_to_domain(self._session, measure)


class SqlAlchemyChecklistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_measure(
        self, max_user_id: int, measure: domain.Measure
    ) -> tuple[domain.UserMeasureChecklist, bool]:
        await _ensure_user(self._session, max_user_id)
        checklist_id = uuid.uuid4()
        created_id = (
            await self._session.execute(
                insert(db.UserMeasureChecklist)
                .values(id=checklist_id, max_user_id=max_user_id, measure_id=measure.id)
                .on_conflict_do_nothing(
                    constraint="uq_user_measure_checklists",
                )
                .returning(db.UserMeasureChecklist.id)
            )
        ).scalar_one_or_none()
        created = created_id is not None
        if created:
            for document in measure.documents:
                await self._session.execute(
                    insert(db.ChecklistDocumentState)
                    .values(
                        id=uuid.uuid4(),
                        checklist_id=checklist_id,
                        measure_document_id=document.id,
                    )
                    .on_conflict_do_nothing(constraint="uq_checklist_document_states")
                )
        return await self._get_by_user_and_measure(max_user_id, measure.id), created

    async def list_by_user(self, max_user_id: int) -> list[domain.UserMeasureChecklist]:
        rows = (
            await self._session.execute(
                select(db.UserMeasureChecklist, db.Measure.name)
                .join(db.Measure, db.UserMeasureChecklist.measure_id == db.Measure.id)
                .where(db.UserMeasureChecklist.max_user_id == max_user_id)
                .order_by(db.UserMeasureChecklist.added_at.desc())
            )
        ).all()
        return [
            await _checklist_to_domain(self._session, checklist, measure_name)
            for checklist, measure_name in rows
        ]

    async def toggle_document(
        self, max_user_id: int, document_state_id: UUID
    ) -> domain.UserMeasureChecklist:
        row = (
            await self._session.execute(
                select(db.ChecklistDocumentState, db.UserMeasureChecklist)
                .join(
                    db.UserMeasureChecklist,
                    db.ChecklistDocumentState.checklist_id == db.UserMeasureChecklist.id,
                )
                .where(
                    db.ChecklistDocumentState.id == document_state_id,
                    db.UserMeasureChecklist.max_user_id == max_user_id,
                )
            )
        ).first()
        if row is None:
            raise ChecklistNotFound(str(document_state_id))
        document_state, checklist = row
        document_state.is_done = not document_state.is_done
        document_state.done_at = datetime.now(UTC) if document_state.is_done else None
        measure_name = (
            await self._session.execute(
                select(db.Measure.name).where(db.Measure.id == checklist.measure_id)
            )
        ).scalar_one()
        return await _checklist_to_domain(self._session, checklist, measure_name)

    async def remove_measure(self, max_user_id: int, measure_id: UUID) -> None:
        await self._session.execute(
            delete(db.UserMeasureChecklist).where(
                db.UserMeasureChecklist.max_user_id == max_user_id,
                db.UserMeasureChecklist.measure_id == measure_id,
            )
        )

    async def _get_by_user_and_measure(
        self, max_user_id: int, measure_id: UUID
    ) -> domain.UserMeasureChecklist:
        row = (
            await self._session.execute(
                select(db.UserMeasureChecklist, db.Measure.name)
                .join(db.Measure, db.UserMeasureChecklist.measure_id == db.Measure.id)
                .where(
                    db.UserMeasureChecklist.max_user_id == max_user_id,
                    db.UserMeasureChecklist.measure_id == measure_id,
                )
            )
        ).one()
        return await _checklist_to_domain(self._session, row[0], row[1])


class SqlAlchemyFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, feedback: domain.Feedback) -> None:
        await _ensure_user(self._session, feedback.max_user_id)
        self._session.add(
            db.MeasureFeedback(
                id=uuid.uuid4(),
                max_user_id=feedback.max_user_id,
                measure_id=feedback.measure_id,
                feedback_type=feedback.feedback_type.value,
                comment=feedback.comment,
            )
        )


class SqlAlchemyInvestorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_prompt_state(self, max_user_id: int) -> InvestorPromptState:
        user = await self._session.get(db.User, max_user_id)
        if user is None:
            return InvestorPromptState.NOT_SHOWN
        return InvestorPromptState(user.investor_prompt_state)

    async def set_prompt_state(self, max_user_id: int, state: InvestorPromptState) -> None:
        await _ensure_user(self._session, max_user_id)
        await self._session.execute(
            update(db.User)
            .where(db.User.max_user_id == max_user_id)
            .values(investor_prompt_state=state.value, updated_at=func.now())
        )

    async def add_lead(self, lead: domain.InvestorLead) -> bool:
        await _ensure_user(self._session, lead.max_user_id)
        lead_id = (
            await self._session.execute(
                insert(db.InvestorLead)
                .values(
                    id=uuid.uuid4(),
                    max_user_id=lead.max_user_id,
                    name=lead.name,
                    contact=lead.contact,
                )
                .on_conflict_do_nothing(index_elements=["max_user_id"])
                .returning(db.InvestorLead.id)
            )
        ).scalar_one_or_none()
        return lead_id is not None


class SqlAlchemyReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def due_checklists(
        self, today: date, days_before: int
    ) -> list[domain.UserMeasureChecklist]:
        target_date = today + timedelta(days=days_before)
        rows = (
            await self._session.execute(
                select(db.UserMeasureChecklist, db.Measure.name)
                .join(db.Measure, db.UserMeasureChecklist.measure_id == db.Measure.id)
                .where(db.Measure.application_deadline.is_not(None))
                .where(db.Measure.application_deadline == target_date)
                .where(
                    ~exists().where(
                        db.ReminderDelivery.max_user_id == db.UserMeasureChecklist.max_user_id,
                        db.ReminderDelivery.measure_id == db.UserMeasureChecklist.measure_id,
                        db.ReminderDelivery.days_before == days_before,
                    )
                )
            )
        ).all()
        return [
            await _checklist_to_domain(self._session, checklist, measure_name)
            for checklist, measure_name in rows
        ]

    async def mark_sent(self, max_user_id: int, measure_id: UUID, days_before: int) -> bool:
        sent_id = (
            await self._session.execute(
                insert(db.ReminderDelivery)
                .values(
                    id=uuid.uuid4(),
                    max_user_id=max_user_id,
                    measure_id=measure_id,
                    days_before=days_before,
                )
                .on_conflict_do_nothing(constraint="uq_reminder_deliveries")
                .returning(db.ReminderDelivery.id)
            )
        ).scalar_one_or_none()
        return sent_id is not None


class SqlAlchemyAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def track(
        self,
        event_type: AnalyticsEventType,
        max_user_id: int | None = None,
        measure_id: UUID | None = None,
        properties: dict[str, object] | None = None,
    ) -> None:
        if max_user_id is not None:
            await _ensure_user(self._session, max_user_id)
        self._session.add(
            db.AnalyticsEvent(
                id=uuid.uuid4(),
                max_user_id=max_user_id,
                measure_id=measure_id,
                event_type=event_type.value,
                properties=properties or {},
            )
        )


async def _ensure_region(session: AsyncSession, code: str | None) -> None:
    if code is not None and await session.get(db.Region, code) is None:
        session.add(db.Region(code=code, name=f"Регион {code}", aliases=[]))


async def _ensure_user(session: AsyncSession, max_user_id: int) -> None:
    stmt = (
        insert(db.User)
        .values(max_user_id=max_user_id, investor_prompt_state=InvestorPromptState.NOT_SHOWN.value)
        .on_conflict_do_update(
            index_elements=["max_user_id"],
            set_={"last_seen_at": func.now(), "updated_at": func.now()},
        )
    )
    await session.execute(stmt)


async def _sphere_id(session: AsyncSession, sphere: SphereCategory | None) -> UUID | None:
    if sphere is None:
        return None
    return (
        await session.execute(
            select(db.SphereCategory.id).where(db.SphereCategory.code == sphere.value)
        )
    ).scalar_one_or_none()


async def _measure_to_domain(session: AsyncSession, measure: db.Measure) -> domain.Measure:
    measure_id = measure.id
    regions = (
        await session.execute(
            select(db.MeasureRegion.region_code).where(db.MeasureRegion.measure_id == measure_id)
        )
    ).scalars()
    sphere_codes = (
        await session.execute(
            select(db.SphereCategory.code)
            .join(db.MeasureSphere, db.MeasureSphere.sphere_category_id == db.SphereCategory.id)
            .where(db.MeasureSphere.measure_id == measure_id)
        )
    ).scalars()
    forms = (
        await session.execute(
            select(db.MeasureBusinessForm.business_form).where(
                db.MeasureBusinessForm.measure_id == measure_id
            )
        )
    ).scalars()
    stages = (
        await session.execute(
            select(db.MeasureBusinessStage.business_stage).where(
                db.MeasureBusinessStage.measure_id == measure_id
            )
        )
    ).scalars()
    msp_categories = (
        await session.execute(
            select(db.MeasureMspCategory.msp_category).where(
                db.MeasureMspCategory.measure_id == measure_id
            )
        )
    ).scalars()
    documents = (
        await session.execute(
            select(db.MeasureDocument)
            .where(db.MeasureDocument.measure_id == measure_id)
            .order_by(db.MeasureDocument.sort_order, db.MeasureDocument.title)
        )
    ).scalars()
    return domain.Measure(
        id=measure.id,
        external_code=measure.external_code,
        name=measure.name,
        support_level=SupportLevel(measure.support_level),
        amount_display=measure.amount_display,
        amount_min_rub=measure.amount_min_rub,
        amount_max_rub=measure.amount_max_rub,
        benefit_detail=measure.benefit_detail,
        what_is_it=measure.what_is_it,
        who_can_receive=measure.who_can_receive,
        where_to_apply=measure.where_to_apply,
        review_days=measure.review_days,
        source_name=measure.source_name,
        source_url=measure.source_url,
        source_checked_at=measure.source_checked_at,
        valid_from=measure.valid_from,
        application_deadline=measure.application_deadline,
        employee_min=measure.employee_min,
        employee_max=measure.employee_max,
        is_active=measure.is_active,
        is_demo=measure.is_demo,
        priority=measure.priority,
        regions=frozenset(regions),
        spheres=frozenset(SphereCategory(code) for code in sphere_codes),
        business_forms=frozenset(BusinessForm(value) for value in forms),
        business_stages=frozenset(BusinessStage(value) for value in stages),
        msp_categories=frozenset(MspCategory(value) for value in msp_categories),
        documents=tuple(
            domain.MeasureDocument(doc.id, doc.measure_id, doc.code, doc.title, doc.sort_order)
            for doc in documents
        ),
    )


async def _checklist_to_domain(
    session: AsyncSession, checklist: db.UserMeasureChecklist, measure_name: str
) -> domain.UserMeasureChecklist:
    rows = (
        await session.execute(
            select(db.ChecklistDocumentState, db.MeasureDocument.title)
            .join(
                db.MeasureDocument,
                db.ChecklistDocumentState.measure_document_id == db.MeasureDocument.id,
            )
            .where(db.ChecklistDocumentState.checklist_id == checklist.id)
            .order_by(db.MeasureDocument.sort_order, db.MeasureDocument.title)
        )
    ).all()
    return domain.UserMeasureChecklist(
        id=checklist.id,
        max_user_id=checklist.max_user_id,
        measure_id=checklist.measure_id,
        measure_name=measure_name,
        added_at=checklist.added_at,
        documents=tuple(
            domain.ChecklistDocumentState(
                id=state.id,
                measure_document_id=state.measure_document_id,
                title=title,
                is_done=state.is_done,
                done_at=state.done_at,
            )
            for state, title in rows
        ),
    )


def _value(value: Any, default: Any = None) -> Any:
    value = default if value is None else value
    return value.value if value is not None else None
