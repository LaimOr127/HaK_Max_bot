import pytest

from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    CompanyLookupStatus,
    ConversationState,
    EmployeeBucket,
    ProfileSource,
    SphereCategory,
)
from navigator.ports.company_lookup import CompanyLookupResult
from navigator.presentation.maxbot.callbacks import parse_callback
from navigator.presentation.maxbot.keyboards import (
    INN_UNAVAILABLE,
    SPHERE,
    WELCOME_BACK,
    ZERO_RESULTS,
)
from navigator.presentation.maxbot.runtime import (
    BotRuntime,
    Incoming,
    _callback_summary,
    _extract_incoming,
    _looks_like_inn,
)


def test_extract_incoming_reads_max_message_body_text() -> None:
    update = {
        "update_type": "message_created",
        "message": {"sender": {"user_id": 42}, "body": {"text": "Привет"}},
    }

    assert _extract_incoming(update) == Incoming(user_id=42, text="Привет")


def test_extract_incoming_turns_bot_started_into_start_command() -> None:
    update = {"update_type": "bot_started", "user": {"user_id": 42}}

    assert _extract_incoming(update) == Incoming(user_id=42, text="/start")


def test_extract_incoming_keeps_media_without_text_out_of_the_form() -> None:
    update = {
        "update_type": "message_created",
        "message": {"sender": {"user_id": 42}, "body": {"attachments": [{"type": "image"}]}},
    }
    assert _extract_incoming(update) == Incoming(user_id=42, text=None)


def test_manual_region_cannot_treat_an_inn_as_a_region() -> None:
    assert _looks_like_inn("9715384111")
    assert _looks_like_inn("342303454473")
    assert not _looks_like_inn("Москва")


def test_saved_profile_actions_keep_recommendations_and_editing_distinct() -> None:
    assert parse_callback("nav:recommend").action == "nav:recommend"
    assert WELCOME_BACK[0]["payload"]["buttons"][0][0]["payload"] == "nav:recommend"


def test_unavailable_fns_and_zero_results_keep_recovery_actions() -> None:
    unavailable = INN_UNAVAILABLE[0]["payload"]["buttons"]
    assert [row[0]["text"] for row in unavailable] == ["Повторить", "Заполнить вручную"]
    empty = ZERO_RESULTS[0]["payload"]["buttons"]
    assert [row[0]["text"] for row in empty] == [
        "Уточнить детали", "Сообщить, чего не хватает"
    ]


def test_callback_summary_keeps_selected_profile_values_readable() -> None:
    assert _callback_summary(parse_callback("sphere:it")) == "IT и цифровые услуги"


def test_every_sphere_button_has_a_valid_callback() -> None:
    for row in SPHERE[0]["payload"]["buttons"]:
        for button in row:
            assert parse_callback(button["payload"]).action in {"sphere", "profile:back"}


@pytest.mark.asyncio
async def test_completed_callback_removes_buttons_but_keeps_profile_text() -> None:
    class MaxClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        async def answer_callback(self, callback_id: str, *, message=None) -> None:
            self.calls.append(("answer", (callback_id, message.to_payload())))

        async def edit_message(self, message_id: str, body: object) -> None:
            self.calls.append(("edit", (message_id, body.to_payload())))

    update = {
        "update_type": "message_callback",
        "message": {"body": {"mid": "message-1", "text": "Профиль"}},
        "callback": {
            "callback_id": "callback-1", "payload": "profile:confirm", "user": {"user_id": 42}
        },
    }
    incoming = _extract_incoming(update)
    assert incoming == Incoming(
        user_id=42,
        callback_payload="profile:confirm",
        callback_id="callback-1",
        callback_message_id="message-1",
    )
    client = MaxClient()
    runtime = object.__new__(BotRuntime)
    runtime._max = client
    await runtime._close_callback(incoming)
    assert client.calls == [("answer", ("callback-1", {"attachments": []}))]


@pytest.mark.asyncio
async def test_start_with_miniapp_sets_inn_state_and_shows_one_app_entry(monkeypatch) -> None:
    class Profiles:
        async def get_by_user(self, user_id):
            assert user_id == 42
            return None

    class States:
        async def set_state(self, user_id, state, context):
            assert user_id == 42
            assert state.value == "AWAITING_INN"
            assert context == {}

    class Session:
        async def __aenter__(self):
            return type(
                "Repos", (), {"profiles": Profiles(), "states": States(), "analytics": None}
            )()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append((user_id, text, keyboard))

    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    runtime._lookup = None
    runtime._miniapp_web_app = "demo_bot"
    await runtime._start(42)
    assert len(sent) == 1
    assert "ИНН" in sent[0][1]
    assert sent[0][2][0]["payload"]["buttons"][0][0]["type"] == "open_app"


@pytest.mark.asyncio
async def test_start_with_complete_profile_shows_recommendations(monkeypatch) -> None:
    profile = BusinessProfile(
        max_user_id=42,
        region_code="77",
        business_form=BusinessForm.OOO,
        sphere=SphereCategory.IT_DIGITAL,
        business_stage=BusinessStage.GT3,
        employee_bucket=EmployeeBucket.OVER_HUNDRED,
    )

    class Profiles:
        async def get_by_user(self, user_id):
            assert user_id == 42
            return profile

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"profiles": Profiles()})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []
    recommended = []

    async def send(self, user_id, text, keyboard=None):
        sent.append((user_id, text, keyboard))

    async def show_recommendations(self, user_id):
        recommended.append(user_id)

    monkeypatch.setattr(BotRuntime, "_send", send)
    monkeypatch.setattr(BotRuntime, "_show_recommendations", show_recommendations)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    runtime._miniapp_web_app = "demo_bot"
    await runtime._start(42)
    assert sent[0][2][0]["payload"]["buttons"][0][0]["type"] == "open_app"
    assert recommended == [42]


@pytest.mark.asyncio
async def test_profile_answers_advance_once_then_confirm(monkeypatch) -> None:
    class States:
        value = (ConversationState.MANUAL_SPHERE, {})

        async def get_state(self, user_id):
            return self.value

        async def set_state(self, user_id, state, context):
            self.value = (state, context)

    class Profiles:
        value = BusinessProfile(max_user_id=42, region_code="77", business_form=BusinessForm.OOO)

        async def get_by_user(self, user_id):
            return self.value

        async def save(self, profile):
            self.value = profile

    states, profiles = States(), Profiles()

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"states": states, "profiles": profiles})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append(text)

    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    monkeypatch.setattr(BotRuntime, "_send", send)

    assert await runtime._handle_profile_answer(42, "sphere", "it")
    assert states.value[0] is ConversationState.MANUAL_STAGE
    assert await runtime._handle_profile_answer(42, "stage", "gt3")
    assert states.value[0] is ConversationState.CONFIRM_PROFILE
    assert not await runtime._handle_profile_answer(42, "sphere", "it")
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_media_does_not_change_conversation_state(monkeypatch) -> None:
    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append(text)

    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    await runtime._handle_text(Incoming(42, text=None))
    assert "только с текстом" in sent[0]


@pytest.mark.asyncio
async def test_one_character_region_repeats_prompt_without_advancing(monkeypatch) -> None:
    class States:
        value = (ConversationState.MANUAL_REGION, {})

        async def get_state(self, user_id):
            return self.value

        async def set_state(self, user_id, state, context):
            self.value = (state, context)

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"states": states})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append(text)

    states = States()
    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    await runtime._handle_text(Incoming(42, text="Ы"))
    assert states.value == (ConversationState.MANUAL_REGION, {})
    assert "укажите регион" in sent[0]


@pytest.mark.asyncio
async def test_returning_user_gets_actions_without_restarting(monkeypatch) -> None:
    profile = BusinessProfile(max_user_id=42, region_code="77")

    class States:
        async def get_state(self, user_id):
            return (ConversationState.READY, {})

    class Profiles:
        async def get_by_user(self, user_id):
            return profile

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"states": States(), "profiles": Profiles()})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append((text, keyboard))

    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    await runtime._handle_text(Incoming(42, text="привет"))
    assert sent[0][0].startswith("С возвращением!")
    assert sent[0][1][0]["payload"]["buttons"][0][0]["payload"] == "nav:recommend"


@pytest.mark.asyncio
async def test_back_from_sphere_keeps_region_and_reasks_form(monkeypatch) -> None:
    class States:
        value = (ConversationState.MANUAL_SPHERE, {"region_code": "77"})

        async def get_state(self, user_id):
            return self.value

        async def set_state(self, user_id, state, context):
            self.value = (state, context)

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"states": states})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append(text)

    states = States()
    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    await runtime._handle_callback(Incoming(42, callback_payload="profile:back"))
    assert states.value == (ConversationState.MANUAL_BUSINESS_FORM, {"region_code": "77"})
    assert sent == ["Какая у вас форма бизнеса?"]


@pytest.mark.asyncio
async def test_confirmed_fns_profile_shows_measures_without_extra_questions(monkeypatch) -> None:
    profile = BusinessProfile(
        max_user_id=42,
        region_code="77",
        business_form=BusinessForm.OOO,
        sphere=SphereCategory.IT_DIGITAL,
        employee_bucket=EmployeeBucket.OVER_HUNDRED,
        source=ProfileSource.FNS,
    )

    class States:
        value = (ConversationState.CONFIRM_PROFILE, {})

        async def set_state(self, user_id, state, context):
            self.value = (state, context)

    class Profiles:
        async def get_by_user(self, user_id):
            return profile

    class Session:
        async def __aenter__(self):
            return type("Repos", (), {"states": states, "profiles": Profiles()})()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    recommended = []

    async def show_recommendations(self, user_id):
        recommended.append(user_id)

    states = States()
    monkeypatch.setattr(BotRuntime, "_show_recommendations", show_recommendations)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    await runtime._after_profile_confirm(42)
    assert states.value == (ConversationState.READY, {})
    assert recommended == [42]


@pytest.mark.asyncio
async def test_fns_lookup_asks_for_missing_staff_before_confirmation(monkeypatch) -> None:
    class States:
        value = None

        async def set_state(self, user_id, state, context):
            self.value = (state, context)

    class Profiles:
        value = None

        async def get_by_user(self, user_id):
            return self.value

        async def save(self, profile):
            self.value = profile

    class Lookup:
        async def find_by_inn(self, inn):
            return CompanyLookupResult(
                CompanyLookupStatus.FOUND,
                inn,
                company_name="Тест",
                region_code="77",
                business_form=BusinessForm.OOO,
                primary_okved="62.01",
            )

    class Session:
        async def __aenter__(self):
            return type(
                "Repos", (), {"states": states, "profiles": profiles, "analytics": None}
            )()

        async def __aexit__(self, *args):
            return None

    class Repos:
        def session(self):
            return Session()

    sent = []

    async def send(self, user_id, text, keyboard=None):
        sent.append((text, keyboard))

    states, profiles = States(), Profiles()
    monkeypatch.setattr(BotRuntime, "_send", send)
    runtime = object.__new__(BotRuntime)
    runtime._repos = Repos()
    runtime._lookup = Lookup()
    await runtime._lookup_inn(42, "7707083893")
    assert states.value[0] is ConversationState.MANUAL_EMPLOYEES
    assert sent[0][0] == "Сколько сотрудников работает в бизнесе?"
