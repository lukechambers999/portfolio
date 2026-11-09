"""
Understat match data: goals and xG for every played match, plus the remaining fixtures.

Each league-season is scraped with understatapi, flattened from Understat's
nested JSON into one row per match, and team names are converted to the
totalcorner.com spellings so the two sources can be joined.
From LT_model.ipynb (Understat fixture scraper, Data clean up, Dataset merging).

When Understat itself is down, finished seasons can be read from the Wayback
Machine's copies of the league pages instead (scrape_season_wayback): those
pages embed the same match JSON (datesData) that understatapi returns.
"""

import re
import time

import pandas as pd
import requests
import understatapi
from understatapi.parsers.base import BaseParser

# Understat league name -> totalcorner league file (top flight and the division below)
LEAGUES = {
    'EPL': {'name': 'Premier League', 'league_tc': 'EnglandPremierLeague', 'league_tc_below': 'EnglandChampionship', 'n_teams_div': 20},
    'La_Liga': {'name': 'La Liga', 'league_tc': 'SpainLaLiga', 'league_tc_below': 'SpainSegunda', 'n_teams_div': 20},
    'Serie_A': {'name': 'Serie A', 'league_tc': 'ItalySerieA', 'league_tc_below': 'ItalySerieB', 'n_teams_div': 20},
    'Bundesliga': {'name': 'Bundesliga', 'league_tc': 'GermanyBundesligaI', 'league_tc_below': 'GermanyBundesligaII', 'n_teams_div': 18},
    'Ligue_1': {'name': 'Ligue 1', 'league_tc': 'FranceLigue1', 'league_tc_below': 'FranceLigue2', 'n_teams_div': 18},
}

FIRST_SEASON = 2015

# Understat name -> totalcorner name, where they differ
NAME_CONV = {
    'Parma Calcio 1913': 'Parma', 'Inter': 'Inter Milan', 'SPAL 2013': 'Spal',
    'Wolverhampton Wanderers': 'Wolverhampton', 'West Bromwich Albion': 'West Brom', 'Sheffield United': 'Sheff Utd',
    'Manchester City': 'Man City', 'Manchester United': 'Man Utd', 'Newcastle United': 'Newcastle', 'Nottingham Forest': 'Nottm Forest',
    'Alaves': 'CD Alaves', 'Real Valladolid': 'Valladolid', 'SD Huesca': 'Huesca', 'Deportivo La Coruna': 'Deportivo A Coruna',
    'Borussia M.Gladbach': 'Borussia M\'gladbach', 'FC Cologne': 'Cologne', 'FC Heidenheim': 'Heidenheim', 'Freiburg': 'SC Freiburg',
    'Greuther Fuerth': 'Greuther Furth',
    'Hamburger SV': 'Hamburg', 'Hoffenheim': 'TSG Hoffenheim', 'Ingolstadt': 'FC Ingolstadt', 'Mainz 05': 'Mainz',
    'Nuernberg': 'Nurnberg', 'RasenBallsport Leipzig': 'RB Leipzig', 'Schalke 04': 'Schalke', 'St. Pauli': 'St Pauli',
    'Fortuna Duesseldorf': 'Fortuna Dusseldorf', 'Ajaccio': 'AC Ajaccio', 'GFC Ajaccio': 'Ajaccio GFCA',
    'Paris Saint Germain': 'PSG', 'Saint-Etienne': 'St Etienne',
}


# Scrapes every season of a league from FIRST_SEASON up to the current one
def scrape_league(league, last_season):
    client = understatapi.UnderstatClient()
    raw_data = []
    for season in range(FIRST_SEASON, last_season + 1):
        df = pd.DataFrame(client.league(league=league).get_match_data(season=str(season)))
        df['season'] = f"{season}/{season + 1}"
        raw_data.append(df)
    return pd.concat(raw_data, ignore_index=True)


# --- Wayback Machine fallback ------------------------------------------------

# understatapi league name -> the path Understat's own URLs use
URL_SLUG = {'EPL': 'EPL', 'La_Liga': 'La_liga', 'Serie_A': 'Serie_A', 'Bundesliga': 'Bundesliga', 'Ligue_1': 'Ligue_1'}
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_RAW = "https://web.archive.org/web/{ts}id_/{url}"  # id_ = the page as archived, without Wayback's toolbar
MAX_SNAPSHOTS = 8  # snapshots tried per season before giving up


def _get(session, url, params=None, tries=4):
    for attempt in range(tries):
        try:
            resp = session.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                return resp
            if resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == tries - 1:
                raise
        time.sleep(5 * (attempt + 1))
    resp.raise_for_status()
    return resp


# Archived copies of a season's league page taken after the season ended (from 1 August of
# its second year, which covers the COVID-delayed 2019/20 finishes), oldest first
def wayback_snapshots(league, season, session):
    url = f"understat.com/league/{URL_SLUG[league]}/{season}"
    resp = _get(session, WAYBACK_CDX, params={"url": url, "filter": "statuscode:200", "from": f"{season + 1}0801",
                                              "fl": "timestamp,original", "collapse": "digest", "output": "json"})
    rows = resp.json() if resp.text.strip() else []
    return [(ts, original) for ts, original in rows[1:]]


# One season's matches from the Wayback Machine, as raw understatapi-style records, plus the
# snapshot used. Tries snapshots oldest first and keeps the one with the most played matches,
# stopping as soon as one has no unplayed fixtures left. Returns (None, None) if nothing parses.
def scrape_season_wayback(league, season, session=None, pause=1.5):
    session = session or requests.Session()
    best, best_ts, best_played = None, None, -1
    for ts, original in wayback_snapshots(league, season, session)[:MAX_SNAPSHOTS]:
        time.sleep(pause)
        html = _get(session, WAYBACK_RAW.format(ts=ts, url=original)).text
        if "datesData" not in html:
            continue  # later page layouts load the data over XHR rather than embedding it
        try:
            records = BaseParser.parse(html=html, query="datesData")
        except ValueError:
            continue
        played = sum(bool(m.get("isResult")) for m in records)
        if played > best_played:
            best, best_ts, best_played = records, ts, played
        if records and played == len(records):
            break
    if best is None:
        return None, None
    df = pd.DataFrame(best)
    df['season'] = f"{season}/{season + 1}"
    return df, best_ts


# Flattens the nested columns, converts types and harmonises team names with totalcorner
def clean(fixtures_data):
    df = fixtures_data.copy()
    for col in ['h', 'a', 'goals', 'xG']:
        flat = pd.json_normalize(df[col])
        flat.columns = [f"{col}_{key}" for key in flat.columns]
        df = pd.concat([df.drop(columns=col), flat], axis=1)

    df = df.rename(columns={'h_title': 'Home', 'a_title': 'Away', 'datetime': 'Date'})
    df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
    df['isResult'] = df['isResult'].astype(bool)
    for col in ['goals_h', 'goals_a', 'xG_h', 'xG_a']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Home'] = df['Home'].replace(NAME_CONV)
    df['Away'] = df['Away'].replace(NAME_CONV)
    return df[['Date', 'season', 'isResult', 'Home', 'Away', 'goals_h', 'goals_a', 'xG_h', 'xG_a']]
