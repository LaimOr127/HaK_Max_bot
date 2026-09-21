from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from navigator.application.checklists import ChecklistService
from navigator.application.dto import FeedbackInput, InvestorLeadInput
from navigator.application.feedback import FeedbackService
from navigator.application.investors import InvestorService
from navigator.domain.entities import (
    ChecklistDocumentState,
    Measure,
    MeasureDocument,
    UserMeasureChecklist,
)
from navigator.domain.enums import (
    AnalyticsEventType,
    FeedbackType,
    InvestorPromptState,
    SupportLevel,
)
from navigator.domain.errors import MeasureNotFound


class FakeAnalytics:
    def __init__(self) -> None:
        self.events = []

    async def track(self, event_type, max_user_id=None, measure_id=None, properties=None) -> None:
        self.events.append((event_type, max_user_id, measure_id, properties))


class FakeMeasures:
    def __init__(self, measure: Measure | None) -> None:
        self.measure = measure

    async def get(self, measure_id: UUID) -> Measure | None:
        return self.measure if self.measure and self.measure.id == measure_id else None


class FakeChecklists:
    def __init__(self) -> None:
        self.items: dict[int, list[UserMeasureChecklist]] = {}
        self.created = True

    async def add_measure(
        self, max_user_id: int, measure: Measure
    ) -> tuple[UserMeasureChecklist, bool]:
        checklist = UserMeasureChecklist(
            id=uuid4(),
            max_user_id=max_user_id,
            measure_id=measure.id,
            measure_name=measure.name,
            added_at=datetime.now(UTC),
            documents=tuple(
                ChecklistDocumentState(uuid4(), document.id, document.title)
                for document in measure.documents
            ),
        )
        self.items.setdefault(max_user_id, []).append(checklist)
        return checklist, self.created

    async def list_by_user(self, max_user_id: int) -> list[UserMeasureChecklist]:
        return self.items.get(max_user_id, [])

    async def toggle_document(
        self, max_user_id: int, document_state_id: UUID
    ) -> UserMeasureChecklist:
        checklist = self.items[max_user_id][0]
        updated_documents = tuple(
            ChecklistDocumentState(doc.id, doc.measure_document_id, doc.title, not doc.is_done)
            if doc.id == document_state_id
            else doc
            for doc in checklist.documents
        )
        updated = UserMeasureChecklist(
            checklist.id,
            checklist.max_user_id,
            checklist.measure_id,
            checklist.measure_name,
            checklist.added_at,
            updated_documents,
        )
        self.items[max_user_id][0] = updated
        return updated

    async def remove_measure(self, max_user_id: int, measure_id: UUID) -> None:
        self.items[max_user_id] = [
            item for item in self.items.get(max_user_id, []) if item.measure_id != measure_id
        ]


class FakeFeedback:
    def __init__(self) -> None:
        self.values = []

    async def add(self, feedback) -> None:
        self.values.append(feedback)


class FakeInvestors:
    def __init__(self, created: bool = True) -> None:
        self.created = created
        self.state = InvestorPromptState.NOT_SHOWN
        self.leads = []

    async def get_prompt_state(self, max_user_id: int) -> InvestorPromptState:
        return self.state

    async def set_prompt_state(self, max_user_id: int, state: InvestorPromptState) -> None:
        self.state = state

    async def add_lead(self, lead) -> bool:
        self.leads.append(lead)
        return self.created


@pytest.mark.asyncio
async def test_add_measure_returns_user_checklist_and_tracks_new_item() -> None:
    measure = _measure()
    analytics = FakeAnalytics()

    dto = await ChecklistService(FakeChecklists(), FakeMeasures(measure), analytics).add_measure(
        42, measure.id
    )

    assert len(dto.checklists) == 1
    assert dto.checklists[0].measure_name == "Grant"
    assert analytics.events == [(AnalyticsEventType.CHECKLIST_ADDED, 42, measure.id, None)]


@pytest.mark.asyncio
async def test_add_measure_rejects_unknown_measure() -> None:
    with pytest.raises(MeasureNotFound):
        await ChecklistService(FakeChecklists(), FakeMeasures(None)).add_measure(42, uuid4())


@pytest.mark.asyncio
async def test_toggle_document_marks_document_done_and_tracks_measure() -> None:
    measure = _measure()
    checklists = FakeChecklists()
    analytics = FakeAnalytics()
    service = ChecklistService(checklists, FakeMeasures(measure), analytics)
    added = await service.add_measure(42, measure.id)

    dto = await service.toggle_document(42, added.checklists[0].documents[0].id)

    assert dto.checklists[0].documents[0].is_done is True
    assert analytics.events[-1] == (
        AnalyticsEventType.CHECKLIST_DOCUMENT_DONE,
        42,
        measure.id,
        None,
    )


@pytest.mark.asyncio
async def test_feedback_submit_stores_feedback_and_tracks_type() -> None:
    repo = FakeFeedback()
    analytics = FakeAnalytics()
    measure_id = uuid4()

    await FeedbackService(repo, analytics).submit(
        FeedbackInput(42, measure_id, FeedbackType.OUTDATED, "old terms")
    )

    assert repo.values[0].comment == "old terms"
    assert analytics.events == [
        (
            AnalyticsEventType.FEEDBACK_SUBMITTED,
            42,
            measure_id,
            {"type": FeedbackType.OUTDATED.value},
        )
    ]


@pytest.mark.asyncio
async def test_investor_submit_interest_marks_prompt_interested() -> None:
    repo = FakeInvestors()

    created = await InvestorService(repo).submit_interest(InvestorLeadInput(42, "Alex", "@alex"))

    assert created is True
    assert repo.state is InvestorPromptState.INTERESTED
    assert repo.leads[0].contact == "@alex"


@pytest.mark.asyncio
async def test_investor_duplicate_interest_does_not_track_analytics() -> None:
    analytics = FakeAnalytics()

    created = await InvestorService(FakeInvestors(created=False), analytics).submit_interest(
        InvestorLeadInput(42, "Alex", "@alex")
    )

    assert created is False
    assert analytics.events == []


def _measure() -> Measure:
    measure_id = uuid4()
    return Measure(
        id=measure_id,
        external_code="DEMO",
        name="Grant",
        support_level=SupportLevel.REGIONAL,
        amount_display="100 rub",
        amount_min_rub=Decimal("100"),
        what_is_it="Grant",
        who_can_receive="Small business",
        where_to_apply="Portal",
        source_name="Source",
        source_url="https://example.com",
            source_checked_at=datetime(2026, 9, 1, tzinfo=UTC).date(),
        documents=(MeasureDocument(uuid4(), measure_id, "application", "Application"),),
    )
