from __future__ import annotations

import streamlit as st
from ui import configure_page

configure_page("Start")
st.title("Gym Tracker")

st.markdown(
    """
### Codzienny workflow

1. **Metryki** - masa, kalorie, sen
2. **Ćwiczenia** - katalog i archiwizacja
3. **Trening** - sesja, serie, 1RM
4. **Historia metryk** - przegląd zakresu dat
5. **Analityka** - trendy i przegląd
"""
)
