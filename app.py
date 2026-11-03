import traceback

import streamlit as st

st.title("Diagnose")
st.write("Schritt 1: Streamlit ✅")
try:
    import stats
    st.write("Schritt 2: stats.py gefunden ✅")

    last = stats.last_completed_week()
    st.write(f"Schritt 3: letzte Woche laut Sleeper = {last} ✅")

    df = stats.fetch_week(1)
    st.write(f"Schritt 4: Woche 1 geladen, {len(df)} Zeilen ✅")

    players = stats.load_players()
    st.write(f"Schritt 5: Spielerliste geladen, {len(players)} Spieler ✅")

    st.write("Schritt 6: zeige Tabelle …")
    st.dataframe(df.head(10))
    st.write("Schritt 7: Tabelle angezeigt ✅")
except Exception:
    st.error("Fehler aufgetreten:")
    st.code(traceback.format_exc())
