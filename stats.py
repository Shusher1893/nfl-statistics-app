"""Daten von der Sleeper-API holen und zu Tabellen aufbereiten."""
import pandas as pd
import requests

SEASON = 2026
MAX_WEEK = 18
STATE_URL = "https://api.sleeper.app/v1/state/nfl"
PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
STATS_URL = "https://api.sleeper.com/stats/nfl/{season}/{week}"  # inoffizieller Endpoint
KEYS = ["pass_yd", "pass_td", "rush_yd", "rush_td", "rec_yd", "rec_td"]

TEAM_OFF = {"pass_yd": "Pass Yards", "pass_td": "Pass TDs",
            "rush_yd": "Rush Yards", "rush_td": "Rush TDs"}
TEAM_DEF = {"pass_yd": "Pass Yards gegen", "pass_td": "Pass TDs gegen",
            "rush_yd": "Rush Yards gegen", "rush_td": "Rush TDs gegen"}
POSITIONS = {
    "Quarterbacks": ("QB", {"pass_yd": "Pass Yards", "pass_td": "Pass TDs",
                            "rush_yd": "Rush Yards", "rush_td": "Rush TDs"}),
    "Wide Receivers": ("WR", {"rec_yd": "Rec Yards", "rec_td": "Rec TDs",
                              "rush_yd": "Rush Yards", "rush_td": "Rush TDs"}),
    "Running Backs": ("RB", {"rush_yd": "Rush Yards", "rush_td": "Rush TDs",
                             "rec_yd": "Rec Yards", "rec_td": "Rec TDs"}),
}


def last_completed_week():
    s = requests.get(STATE_URL, timeout=30).json()
    season = int(s.get("season", SEASON))
    if season > SEASON:
        return MAX_WEEK
    if season < SEASON or s.get("season_type") == "pre":
        return 0
    return min(int(s.get("week", 0)), MAX_WEEK)


def fetch_week(week):
    r = requests.get(STATS_URL.format(season=SEASON, week=week),
                     params={"season_type": "regular"}, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return pd.DataFrame()
    if not isinstance(rows, list):
        raise RuntimeError("Unerwartetes Datenformat von Sleeper (Endpoint geändert?)")
    recs = []
    for row in rows:
        st = row.get("stats") or {}
        if not any(k in st for k in KEYS):
            continue
        rec = {"player_id": str(row.get("player_id")), "team": row.get("team"),
               "opponent": row.get("opponent"), "week": week}
        for k in KEYS:
            rec[k] = st.get(k) or 0
        recs.append(rec)
    return pd.DataFrame(recs)


def load_stats():
    """Alle Wochen der Saison bis zur letzten gespielten Woche laden."""
    last = last_completed_week()
    frames = [fetch_week(w) for w in range(1, last + 1)]
    frames = [f for f in frames if not f.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return df, last


def load_players():
    data = requests.get(PLAYERS_URL, timeout=120).json()
    rows = []
    for pid, p in data.items():
        if p.get("position") in ("QB", "RB", "WR"):
            name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            rows.append({"player_id": str(pid), "Name": name, "position": p["position"]})
    return pd.DataFrame(rows)


def _team_table(df, by, cols, label):
    g = df.dropna(subset=[by]).groupby(by)[list(cols)].sum().astype(int)
    g = g.rename(columns=cols)
    g.index.name = label
    return g.reset_index()


def team_offense(df):
    return _team_table(df, "team", TEAM_OFF, "Team")


def team_defense(df):
    # Defense = was der jeweilige Gegner gegen das Team erzielt hat
    return _team_table(df, "opponent", TEAM_DEF, "Team")


def player_table(df, players, position, cols):
    g = df.groupby("player_id")[list(cols)].sum()
    team = df.sort_values("week").groupby("player_id")["team"].last().rename("Team")
    t = players[players["position"] == position].set_index("player_id")
    t = t[["Name"]].join(g, how="inner").join(team)
    t = t[t[list(cols)].sum(axis=1) > 0].rename(columns=cols)
    t[list(cols.values())] = t[list(cols.values())].astype(int)
    return t[["Name", "Team"] + list(cols.values())].reset_index(drop=True)
