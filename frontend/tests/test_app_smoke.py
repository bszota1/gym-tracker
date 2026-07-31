from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def test_home_page_renders() -> None:
    app = AppTest.from_file("frontend/Gym_Tracker.py", default_timeout=10).run()
    assert not app.exception
    assert "Gym Tracker" in app.title[0].value
    assert any("Codzienny workflow" in block.value for block in app.markdown)


def test_training_page_does_not_auto_create_session() -> None:
    with (
        patch("ui.check_health", return_value=(True, "API OK")),
        patch("data_cache.cached_list_sessions", return_value=[]),
        patch("data_cache.cached_list_exercises", return_value=[]),
        patch("api_client.create_session") as create_session,
    ):
        app = AppTest.from_file("frontend/pages/4_Trening.py", default_timeout=10).run()

    assert not app.exception
    create_session.assert_not_called()
    assert any(button.label == "Utwórz sesję" for button in app.button)
