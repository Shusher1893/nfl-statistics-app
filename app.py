import streamlit as st

import stats

st.set_page_config(page_title="NFL Manager-Stats", page_icon="🏈", layout="wide")


@st.cache_data(ttl=6 * 3600, show_spinner="Lade Spielstatistiken …")
def get_stats():
    return stats.load_stats()


@st.cache_data(ttl=24 * 3600, show_spinner="Lade Spielerliste …")
def get_players():
    return stats.load_players()


st.title(f"🏈 NFL Manager-Stats {stats.SEASON}")

try:
    df, last_week = get_stats()
    players = get_players()
except Exception as e:
    st.error(f"Daten konnten nicht geladen werden: {e}")
    st.stop()

if df.empty:
    st.info("Noch keine Spieldaten für diese Saison verfügbar.")
    st.stop()

st.caption(f"Stand: bis Woche {last_week} · Quelle: Sleeper API (aktualisiert sich automatisch)")
if st.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()


def show(table, key, search=False):
    if table.empty:
        st.info("Keine Daten verfügbar.")
        return
    stat_cols = [c for c in table.columns if c not in ("Team", "Name")]
    c1, c2 = st.columns(2)
    sort_by = c1.selectbox("Sortieren nach", stat_cols, key=f"s_{key}")
    order = c2.radio("Reihenfolge", ["Absteigend", "Aufsteigend"], horizontal=True, key=f"o_{key}")
    if search:
        q = st.text_input("Suche (Name oder Team)", key=f"q_{key}")
        if q:
            mask = table["Name"].str.contains(q, case=False, na=False) | \
                   table["Team"].astype(str).str.contains(q, case=False, na=False)
            table = table[mask]
    table = table.sort_values(sort_by, ascending=(order == "Aufsteigend"))
    st.dataframe(table, hide_index=True)


tabs = st.tabs(["Teams Offense", "Teams Defense", "Quarterbacks", "Wide Receivers", "Running Backs"])
with tabs[0]:
    show(stats.team_offense(df), "off")
with tabs[1]:
    show(stats.team_defense(df), "def")
for tab, (label, (pos, cols)) in zip(tabs[2:], stats.POSITIONS.items()):
    with tab:
        show(stats.player_table(df, players, pos, cols), pos, search=True)
