"""
FotMob match data: goals and Opta xG for every played match, plus the remaining fixtures.

Each league-season's fixture list comes from FotMob's league endpoint, which has scores
but no xG; xG is read from each played match's own details endpoint, one request per
match. Match xG is cached to disk so a re-run only fetches matches it has not seen.
Output columns match understat.clean(), plus the league name.
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

API = 'https://www.fotmob.com/api/data'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
DELAY = 0.5  # seconds between match requests

# FotMob league id -> league name, and the first season FotMob has xG for
LEAGUES = {
    108: {'name': 'League One', 'first_season': 2022},
}


def get(endpoint, **params):
    r = requests.get(f"{API}/{endpoint}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


# One row per league match in a season (play-off rounds dropped, as Understat has none)
def season_fixtures(league_id, season):
    data = get('leagues', id=league_id, season=f"{season}/{season + 1}")
    rows = []
    for m in data['fixtures']['allMatches']:
        if not str(m['round']).isdigit():
            continue
        status = m['status']
        goals_h = goals_a = None
        if status.get('finished') and not status.get('cancelled') and 'scoreStr' in status:
            goals_h, goals_a = (int(g) for g in status['scoreStr'].split(' - '))
        rows.append({
            'matchid': m['id'], 'Date': status['utcTime'], 'season': f"{season}/{season + 1}",
            'isResult': goals_h is not None, 'Home': m['home']['name'], 'Away': m['away']['name'],
            'goals_h': goals_h, 'goals_a': goals_a,
        })
    return rows


# Home and away xG from a match's details, or (None, None) if FotMob has no xG for it
def match_xg(match_id):
    details = get('matchDetails', matchId=match_id)
    periods = ((details.get('content') or {}).get('stats') or {}).get('Periods') or {}
    for group in (periods.get('All') or {}).get('stats', []):
        for stat in group.get('stats', []):
            if stat.get('key') == 'expected_goals' and stat['stats'][0] is not None:
                return tuple(float(x) for x in stat['stats'])
    return None, None


# Scrapes every season of a league from its first xG season up to last_season.
# cache is a JSON file of match id -> [xG_h, xG_a] for played matches.
def scrape_league(league_id, last_season, cache=None):
    xg = json.loads(Path(cache).read_text()) if cache and Path(cache).exists() else {}
    rows = []
    for season in range(LEAGUES[league_id]['first_season'], last_season + 1):
        rows += season_fixtures(league_id, season)

    todo = [r['matchid'] for r in rows if r['isResult'] and r['matchid'] not in xg]
    for i, match_id in enumerate(todo, 1):
        xg[match_id] = match_xg(match_id)
        if cache and (i % 50 == 0 or i == len(todo)):
            Path(cache).write_text(json.dumps(xg))
        time.sleep(DELAY)

    df = pd.DataFrame(rows)
    df['league'] = LEAGUES[league_id]['name']
    df['xG_h'] = [xg.get(m, (None, None))[0] for m in df['matchid']]
    df['xG_a'] = [xg.get(m, (None, None))[1] for m in df['matchid']]
    return df


# Converts types into the same shape as understat.clean()
def clean(fixtures_data):
    df = fixtures_data.copy()
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None).dt.normalize()
    for col in ['goals_h', 'goals_a', 'xG_h', 'xG_a']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df[['league', 'Date', 'season', 'isResult', 'Home', 'Away', 'goals_h', 'goals_a', 'xG_h', 'xG_a']]
