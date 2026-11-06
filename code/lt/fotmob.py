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
    47: {'name': 'Premier League', 'first_season': 2020},
    87: {'name': 'La Liga', 'first_season': 2020},
    55: {'name': 'Serie A', 'first_season': 2020},
    54: {'name': 'Bundesliga', 'first_season': 2020},
    53: {'name': 'Ligue 1', 'first_season': 2020},
    108: {'name': 'League One', 'first_season': 2022},
}

# FotMob name -> totalcorner name, where they differ (top-5 leagues, 2020/21 on; League One not yet done).
# Found by pairing each FotMob fixture with the totalcorner fixture on the same date.
NAME_CONV = {
    # England
    'AFC Bournemouth': 'Bournemouth', 'Brighton & Hove Albion': 'Brighton', 'Coventry City': 'Coventry',
    'Hull City': 'Hull', 'Ipswich Town': 'Ipswich', 'Leeds United': 'Leeds', 'Leicester City': 'Leicester',
    'Luton Town': 'Luton', 'Manchester City': 'Man City', 'Manchester United': 'Man Utd',
    'Newcastle United': 'Newcastle', 'Norwich City': 'Norwich', 'Nottingham Forest': 'Nottm Forest',
    'Sheffield United': 'Sheff Utd', 'Tottenham Hotspur': 'Tottenham', 'West Bromwich Albion': 'West Brom',
    'West Ham United': 'West Ham', 'Wolverhampton Wanderers': 'Wolverhampton',
    # Spain
    'Almería': 'Almeria', 'Atlético Madrid': 'Atletico Madrid', 'Cádiz': 'Cadiz',
    'Deportivo A Coruña': 'Deportivo A Coruna', 'Deportivo Alavés': 'CD Alaves', 'Leganés': 'Leganes',
    'Málaga': 'Malaga', 'Real Valladolid': 'Valladolid', 'SD Huesca': 'Huesca',
    # Italy
    'Hellas Verona': 'Verona', 'Inter': 'Inter Milan', 'Milan': 'AC Milan',
    # Germany
    '1. FC Köln': 'Cologne', 'Bayern München': 'Bayern Munich', 'Borussia Mönchengladbach': 'Borussia M\'gladbach',
    'FC Heidenheim': 'Heidenheim', 'Freiburg': 'SC Freiburg', 'Greuther Fürth': 'Greuther Furth',
    'Hamburger SV': 'Hamburg', 'Hertha BSC': 'Hertha Berlin', 'Hoffenheim': 'TSG Hoffenheim', 'Mainz 05': 'Mainz',
    'Schalke 04': 'Schalke', 'St. Pauli': 'St Pauli',
    # France
    'Nîmes': 'Nimes', 'Paris Saint-Germain': 'PSG', 'Saint-Étienne': 'St Etienne',
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


# Converts types into the same shape as understat.clean() and harmonises team names with totalcorner
def clean(fixtures_data):
    df = fixtures_data.copy()
    df['Home'] = df['Home'].replace(NAME_CONV)
    df['Away'] = df['Away'].replace(NAME_CONV)
    # utcTime comes both with and without milliseconds
    df['Date'] = pd.to_datetime(df['Date'], format='ISO8601').dt.tz_localize(None).dt.normalize()
    for col in ['goals_h', 'goals_a', 'xG_h', 'xG_a']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df[['league', 'Date', 'season', 'isResult', 'Home', 'Away', 'goals_h', 'goals_a', 'xG_h', 'xG_a']]
