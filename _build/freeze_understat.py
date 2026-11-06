"""
Saves Understat's goals and xG for the seasons before FotMob's xG starts (2015/16 to 2019/20)
to data/understat/<League>.csv, for make_lt_snapshots.py to use as the older history.

Those seasons are finished, so this only needs running once (or again to re-check them).
Run from the repo root:
  .venv/Scripts/python _build/freeze_understat.py [--leagues EPL Serie_A]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code" / "lt"))
sys.path.insert(0, str(ROOT / "_build"))
import understat  # noqa: E402
import fotmob  # noqa: E402
from make_lt_snapshots import FOTMOB_IDS, UNDERSTAT_DIR  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leagues", nargs="+", default=list(understat.LEAGUES), choices=list(understat.LEAGUES))
    args = ap.parse_args()
    UNDERSTAT_DIR.mkdir(parents=True, exist_ok=True)

    for lg in args.leagues:
        last_season = fotmob.LEAGUES[FOTMOB_IDS[lg]]["first_season"] - 1
        df = understat.clean(understat.scrape_league(lg, last_season))
        df.to_csv(UNDERSTAT_DIR / f"{lg}.csv", index=False)
        played = df[df["isResult"]]
        print(f"{lg}: {len(played)} played matches, {df['season'].min()} to {df['season'].max()}, "
              f"{played['xG_h'].isna().sum()} without xG")


if __name__ == "__main__":
    main()
