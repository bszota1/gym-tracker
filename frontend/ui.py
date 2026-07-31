from __future__ import annotations

import streamlit as st
from api_client import check_health
from api_errors import ApiClientError


def configure_page(title: str, *, layout: str = "centered") -> None:
    st.set_page_config(
        page_title=f"{title} · Gym Tracker",
        page_icon=None,
        layout=layout,
    )


def check_api_available(*, force: bool = False) -> bool:
    if force or "api_ok" not in st.session_state:
        ok, message = check_health()
        st.session_state["api_ok"] = ok
        st.session_state["api_message"] = message
    return bool(st.session_state.get("api_ok", False))


def show_api_error(exc: Exception) -> None:
    if isinstance(exc, ApiClientError):
        st.error(exc.user_message())
        return
    st.error("Wystąpił nieoczekiwany błąd. Spróbuj ponownie.")


def show_warning(message: str) -> None:
    st.warning(message)


def empty_state(message: str, *, next_step: str | None = None) -> None:
    st.info(message)
    if next_step:
        st.caption(next_step)
