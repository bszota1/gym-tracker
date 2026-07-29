import streamlit as st
from api_client import check_health, get_api_base_url, get_api_root

st.set_page_config(page_title="Gym Tracker", page_icon=None, layout="centered")
st.title("Gym Tracker")
st.caption("Lokalna aplikacja treningowo-analityczna")

st.subheader("Połączenie z API")
st.write(f"API root: `{get_api_root()}`")
st.write(f"API base URL: `{get_api_base_url()}`")

if st.button("Sprawdź /health"):
    ok, message = check_health()
    if ok:
        st.success(message)
    else:
        st.error(message)
else:
    st.info("Kliknij przycisk, aby sprawdzić dostępność FastAPI.")
