from __future__ import annotations

import streamlit as st
from api_client import (
    apply_import,
    apply_import_from_export,
    create_backup,
    create_export,
    dry_run_import,
    list_backups,
    list_exports,
)
from api_errors import ApiClientError
from data_cache import invalidate_all_reads
from ui import check_api_available, configure_page, empty_state, show_api_error

configure_page("Dane")
st.title("Eksport, import i backup")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

st.caption(
    "Backup używa SQLite Backup API. Import najpierw robi dry-run, potem backup, "
    "potem podmienia dane w jednej transakcji."
)

st.subheader("Backup")
if st.button("Utwórz backup", type="primary"):
    try:
        result = create_backup()
        st.success(f"Backup: {result['filename']}")
        st.caption(result["path"])
    except ApiClientError as exc:
        show_api_error(exc)

try:
    backups = list_backups()
except ApiClientError as exc:
    show_api_error(exc)
    backups = []

if not backups:
    empty_state("Brak backupów.", next_step="Utwórz pierwszą kopię przyciskiem powyżej.")
else:
    for item in backups[:10]:
        st.write(f"**{item['filename']}** · {item.get('size_bytes', '?')} B")

st.divider()
st.subheader("Eksport")
if st.button("Eksportuj dane do ZIP"):
    try:
        result = create_export()
        st.success(f"Eksport: {result['filename']}")
        st.json(result.get("row_counts", {}))
        st.caption(result["path"])
    except ApiClientError as exc:
        show_api_error(exc)

try:
    exports = list_exports()
except ApiClientError as exc:
    show_api_error(exc)
    exports = []

if not exports:
    st.caption("Brak plików eksportu.")
else:
    for item in exports[:10]:
        st.write(f"**{item['filename']}** · {item.get('size_bytes', '?')} B")

st.divider()
st.subheader("Import")
uploaded = st.file_uploader("Paczka ZIP z eksportu", type=["zip"])
col_dry, col_apply = st.columns(2)

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    with col_dry:
        if st.button("Dry-run"):
            try:
                report = dry_run_import(uploaded.name, file_bytes)
                if report.get("ok"):
                    st.success("Walidacja OK — można importować.")
                else:
                    st.warning("Znaleziono konflikty.")
                st.json(report)
            except ApiClientError as exc:
                show_api_error(exc)
    with col_apply:
        confirm = st.checkbox("Potwierdzam nadpisanie lokalnych danych")
        if st.button("Importuj", type="primary", disabled=not confirm):
            try:
                result = apply_import(uploaded.name, file_bytes)
                invalidate_all_reads()
                st.success("Import zakończony.")
                st.json(result)
            except ApiClientError as exc:
                show_api_error(exc)

if exports:
    st.caption("Albo zaimportuj ostatni eksport z serwera:")
    chosen = st.selectbox(
        "Plik eksportu na serwerze",
        options=[item["filename"] for item in exports],
    )
    confirm_server = st.checkbox(
        "Potwierdzam import z pliku serwera",
        key="confirm_server_import",
    )
    if st.button("Importuj z serwera", disabled=not confirm_server):
        try:
            result = apply_import_from_export(chosen)
            invalidate_all_reads()
            st.success("Import z serwera zakończony.")
            st.json(result)
        except ApiClientError as exc:
            show_api_error(exc)
