import datetime

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


@st.cache_data(ttl=3600, show_spinner=False)
def get_schedule():
    return stats.load_schedule()


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


def _sort(key, col):
    if st.session_state.get(f"sort_{key}") == col:
        st.session_state[f"asc_{key}"] = not st.session_state.get(f"asc_{key}", False)
    else:
        st.session_state[f"sort_{key}"] = col
        st.session_state[f"asc_{key}"] = False


def _toggle(k):
    st.session_state[k] = not st.session_state.get(k, False)


def to_md(df):
    head = "| # | " + " | ".join(df.columns) + " |"
    sep = "|---:|" + "|".join("---" if c in ("Team", "Name") else "---:" for c in df.columns) + "|"
    rows = [
        f"| {i} | " + " | ".join(str(v).replace("|", "/") for v in r) + " |"
        for i, r in enumerate(df.itertuples(index=False), 1)
    ]
    return "\n".join([head, sep, *rows])


def show(table, key):
    if table.empty:
        st.info("Keine Daten verfügbar.")
        return
    stat_cols = [c for c in table.columns if c not in ("Team", "Name")]
    sort_by = st.session_state.get(f"sort_{key}", stat_cols[0])
    asc = st.session_state.get(f"asc_{key}", False)
    st.caption("Tippe auf eine Statistik zum Sortieren, nochmal tippen kehrt die Reihenfolge um.")
    for c, name in zip(st.columns([1] * len(stat_cols) + [2], gap="small"), stat_cols):
        arrow = (" ▲" if asc else " ▼") if name == sort_by else ""
        c.button(name + arrow, key=f"b_{key}_{name}", on_click=_sort, args=(key, name))
    table = table.sort_values(sort_by, ascending=asc)
    show_all = st.session_state.get(f"all_{key}", False)
    st.markdown(to_md(table if show_all else table.head(50)))
    if len(table) > 50:
        label = "Nur Top 50 anzeigen" if show_all else f"Alle {len(table)} anzeigen"
        st.button(label, key=f"all_btn_{key}", on_click=_toggle, args=(f"all_{key}",))


DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _fmt_date(d):
    try:
        dt = datetime.date.fromisoformat(str(d)[:10])
        return f"{DAYS[dt.weekday()]} {dt.day:02d}.{dt.month:02d}."
    except Exception:
        return "Termin offen"


def _result(g):
    if g.status == "canceled":
        return " – abgesagt"
    if g.status == "in_game":
        return " – läuft"
    if g.status == "complete":
        if pd.notna(g.away_score) and pd.notna(g.home_score):
            return f" – {int(g.away_score)}:{int(g.home_score)}"
        return " – beendet"
    return ""


def _set_week(w):
    st.session_state["sched_week"] = w


def show_schedule(current):
    st.subheader("Spielplan")
    try:
        sched = get_schedule()
    except Exception as e:
        st.info(f"Spielplan konnte nicht geladen werden: {e}")
        return
    if sched.empty:
        st.info("Kein Spielplan verfügbar.")
        return
    current = max(1, min(current, stats.MAX_WEEK))
    week = st.session_state.get("sched_week", current)

    c1, c2, c3 = st.columns([1, 1, 4], gap="small")
    c1.button("◀", key="wk_prev", on_click=_set_week, args=(max(1, week - 1),))
    c2.button("▶", key="wk_next", on_click=_set_week, args=(min(stats.MAX_WEEK, week + 1),))
    c3.markdown(f"**Woche {week}**" + (" (aktuell)" if week == current else ""))
    with st.expander("Woche direkt wählen"):
        for first in range(1, stats.MAX_WEEK + 1, 6):
            for c, w in zip(st.columns(6, gap="small"), range(first, first + 6)):
                c.button(str(w), key=f"wk_{w}", on_click=_set_week, args=(w,))

    games = sched[sched["week"] == week].sort_values("date", na_position="last")
    if games.empty:
        st.info("Keine Spiele in dieser Woche.")
        return
    lines, last_day = [], None
    for g in games.itertuples():
        day = _fmt_date(g.date)
        if day != last_day:
            lines.append(f"\n**{day}**\n")
            last_day = day
        lines.append(f"- {g.away} @ {g.home}{_result(g)}")
    st.markdown("\n".join(lines))
    all_teams = set(sched["away"]) | set(sched["home"])
    bye = sorted(all_teams - set(games["away"]) - set(games["home"]))
    if bye:
        st.caption("Spielfrei: " + ", ".join(bye))


main, side = st.columns([2, 1], gap="large")
with main:
    tabs = st.tabs(["Teams Offense", "Teams Defense", "Quarterbacks", "Wide Receivers", "Running Backs"])
    with tabs[0]:
        show(stats.team_offense(df), "off")
    with tabs[1]:
        show(stats.team_defense(df), "def")
    for tab, (label, (pos, cols)) in zip(tabs[2:], stats.POSITIONS.items()):
        with tab:
            show(stats.player_table(df, players, pos, cols), pos)
with side:
    show_schedule(last_week)
