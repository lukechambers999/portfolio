"""
Saves Understat's goals and xG for the seasons before FotMob's xG starts (2015/16 to 2019/20)
to data/understat/<League>.csv, for make_lt_snapshots.py to use as the older history.

Those seasons are finished, so this only needs running once (or again to re-check them).
Run from the repo root:
  .venv/Scripts/python _build/freeze_understat.py [--leagues EPL Serie_A] [--source auto|live|wayback]

--source auto (the default) scrapes Understat directly and, if that fails (for example while
the site is down), reads each season from the Wayback Machine's archived league pages instead.
data/understat/sources.csv records where every league-season came from (the snapshot timestamp
for Wayback seasons). Seasons that neither source has are reported and left out.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "lt"))
sys.path.insert(0, str(ROOT / "_build"))
import understat  # noqa: E402
import fotmob  # noqa: E402
from make_lt_snapshots import FOTMOB_IDS, UNDERSTAT_DIR  # noqa: E402

SOURCES = UNDERSTAT_DIR / "sources.csv"


def scrape_live(lg, last_season):
    raw = understat.scrape_league(lg, last_season)
    seasons = range(understat.FIRST_SEASON, last_season + 1)
    return raw, [{"league": lg, "season": f"{s}/{s + 1}", "source": "understat", "snapshot": ""} for s in seasons]


def scrape_wayback(lg, last_season, session):
    parts, sources = [], []
    for s in range(understat.FIRST_SEASON, last_season + 1):
        df, ts = understat.scrape_season_wayback(lg, s, session=session)
        season = f"{s}/{s + 1}"
        if df is None:
            print(f"  {lg} {season}: no usable Wayback snapshot - left out")
            sources.append({"league": lg, "season": season, "source": "missing", "snapshot": ""})
            continue
        played = int(df["isResult"].astype(bool).sum())
        print(f"  {lg} {season}: {played}/{len(df)} played, snapshot {ts}")
        parts.append(df)
        sources.append({"league": lg, "season": season, "source": "wayback", "snapshot": ts})
    raw = pd.concat(parts, ignore_index=True) if parts else None
    return raw, sources


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leagues", nargs="+", default=list(understat.LEAGUES), choices=list(understat.LEAGUES))
    ap.add_argument("--source", choices=["auto", "live", "wayback"], default="auto")
    args = ap.parse_args()
    UNDERSTAT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "portfolio-lt-model/1.0 (historical xG backfill)"

    all_sources = pd.read_csv(SOURCES, dtype=str).fillna("") if SOURCES.exists() else pd.DataFrame()
    for lg in args.leagues:
        last_season = fotmob.LEAGUES[FOTMOB_IDS[lg]]["first_season"] - 1
        raw = None
        if args.source in ("auto", "live"):
            try:
                raw, sources = scrape_live(lg, last_season)
            except Exception as e:  # understatapi raises a variety of errors when the site is down
                if args.source == "live":
                    raise
                print(f"{lg}: Understat unavailable ({type(e).__name__}: {e}) - using the Wayback Machine")
        if raw is None:
            raw, sources = scrape_wayback(lg, last_season, session)
        if raw is None:
            print(f"{lg}: nothing found, no file written")
            continue

        df = understat.clean(raw)
        df.to_csv(UNDERSTAT_DIR / f"{lg}.csv", index=False)
        played = df[df["isResult"]]
        print(f"{lg}: {len(played)} played matches, {df['season'].min()} to {df['season'].max()}, "
              f"{played['xG_h'].isna().sum()} without xG")
        if not all_sources.empty:
            all_sources = all_sources[all_sources["league"] != lg]
        all_sources = pd.concat([all_sources, pd.DataFrame(sources)], ignore_index=True)
        all_sources.to_csv(SOURCES, index=False)


if __name__ == "__main__":
    main()
