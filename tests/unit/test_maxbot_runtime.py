from navigator.presentation.maxbot.runtime import Incoming, _extract_incoming


def test_extract_incoming_reads_max_message_body_text() -> None:
    update = {
        "update_type": "message_created",
        "message": {"sender": {"user_id": 42}, "body": {"text": "Привет"}},
    }

    assert _extract_incoming(update) == Incoming(user_id=42, text="Привет")


def test_extract_incoming_turns_bot_started_into_start_command() -> None:
    update = {"update_type": "bot_started", "user": {"user_id": 42}}

    assert _extract_incoming(update) == Incoming(user_id=42, text="/start")
