from navigator.presentation.maxbot.callbacks import parse_callback
from navigator.presentation.maxbot.keyboards import WELCOME_BACK
from navigator.presentation.maxbot.runtime import Incoming, _extract_incoming, _looks_like_inn


def test_extract_incoming_reads_max_message_body_text() -> None:
    update = {
        "update_type": "message_created",
        "message": {"sender": {"user_id": 42}, "body": {"text": "Привет"}},
    }

    assert _extract_incoming(update) == Incoming(user_id=42, text="Привет")


def test_extract_incoming_turns_bot_started_into_start_command() -> None:
    update = {"update_type": "bot_started", "user": {"user_id": 42}}

    assert _extract_incoming(update) == Incoming(user_id=42, text="/start")


def test_manual_region_cannot_treat_an_inn_as_a_region() -> None:
    assert _looks_like_inn("9715384111")
    assert _looks_like_inn("342303454473")
    assert not _looks_like_inn("Москва")


def test_saved_profile_actions_keep_recommendations_and_editing_distinct() -> None:
    assert parse_callback("nav:recommend").action == "nav:recommend"
    assert WELCOME_BACK[0]["payload"]["buttons"][0][0]["payload"] == "nav:recommend"
