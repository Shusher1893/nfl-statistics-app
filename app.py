import pandas as pd
import streamlit as st

import stats

st.set_page_config(page_title="NFL Manager-Stats", page_icon="🏈", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def get_last_week():
    return stats.last_completed_week()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_week(week):
    return stats.fetch_week(week)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def get_players():
    return stats.load_players()


st.title(f"🏈 NFL Manager-Stats {stats.SEASON}")

bar = st.progress(0, text="Starte …")
try:
    last_week = get_last_week()
    frames = []
    for w in range(1, last_week + 1):
        bar.progress(w / last_week, text=f"Lade Woche {w} von {last_week} …")
        f = get_week(w)
        if not f.empty:
            frames.append(f)
    bar.progress(1.0, text="Lade Spielerliste (große Datei, beim ersten Mal etwas Geduld) …")
    players = get_players()
except Exception as e:
    bar.empty()
    st.error(f"Daten konnten nicht geladen werden: {e}")
    st.stop()
bar.empty()

if not frames:
    st.info("Noch keine Spieldaten für diese Saison verfügbar.")
    st.stop()
df = pd.concat(frames, ignore_index=True)

st.caption(f"Stand: bis Woche {last_week} · Quelle: Sleeper API (aktualisiert sich automatisch)")
if st.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()


def show(table, key, search=False):
    if table.empty:
        st.info("Keine Daten verfügbar.")
        return
    stat_cols = [c for c in table.columns if c not in ("Team", "Name")]
    c1, c2, c3 = st.columns(3)
    sort_by = c1.selectbox("Sortieren nach", stat_cols, key=f"s_{key}")
    order = c2.radio("Reihenfolge", ["Absteigend", "Aufsteigend"], horizontal=True, key=f"o_{key}")
    n = c3.selectbox("Zeilen anzeigen", [25, 50, 100, 300], index=1, key=f"n_{key}")
    if search:
        q = st.text_input("Suche (Name oder Team)", key=f"q_{key}")
        if q:
            mask = table["Name"].str.contains(q, case=False, na=False) | \
                   table["Team"].astype(str).str.contains(q, case=False, na=False)
            table = table[mask]
    table = table.sort_values(sort_by, ascending=(order == "Aufsteigend"))
    table = table.head(n).reset_index(drop=True)
    table.index = table.index + 1  # Rang
    st.table(table)


tabs = st.tabs(["Teams Offense", "Teams Defense", "Quarterbacks", "Wide Receivers", "Running Backs"])
with tabs[0]:
    show(stats.team_offense(df), "off")
with tabs[1]:
    show(stats.team_defense(df), "def")
for tab, (label, (pos, cols)) in zip(tabs[2:], stats.POSITIONS.items()):
    with tab:
        show(stats.player_table(df, players, pos, cols), pos, search=True)
