import streamlit as st

st.title("Test: Streamlit läuft ✅")
st.write("Lade pandas …")
import pandas as pd
st.write(f"pandas {pd.__version__} ✅")
import requests
st.write("requests ✅")
r = requests.get("https://api.sleeper.app/v1/state/nfl", timeout=(10, 30))
st.write("Sleeper erreichbar ✅", r.json())
