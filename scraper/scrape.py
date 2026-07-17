#!/usr/bin/env python3
"""
NARCH 40 & Over finals scraper.

Talks to the DigitalShift API that powers narch.com/stats, pulls the schedule
and standings for the 40 & Over division, parses them into clean JSON, and
writes docs/data/latest.json for the static site to render.

Pure standard library — no pip installs, so it runs on a bare GitHub Actions
runner with zero setup.
"""

import html
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# --- Configuration (discovered from the live narch.com/stats app) -----------
CLIENT_SERVICE_ID = "fbc8b65d-927d-4b2c-838b-65a128f318c4"
API_BASE = "https://web.api.digitalshift.ca"
LEAGUE_ID = 67
DIVISION_ID = 50812  # "40 & Over"

# The team we spotlight. Matched primarily by id, with a name fallback so it
# keeps working even if ids ever change.
GOODLIFE_TEAM_ID = 690228
GOODLIFE_NAME_HINT = "goodlife"

OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "docs", "data", "latest.json"
)

TIMEOUT = 30


def _request(url, method="GET", body=None):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "narch-40over-tracker/1.0 (+github actions)",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


def login():
    """Get a short-lived anonymous API ticket, same as the website does."""
    raw = _request(
        f"{API_BASE}/login",
        method="POST",
        body={"client_service_id": CLIENT_SERVICE_ID},
    )
    ticket = json.loads(raw).get("ticket", {}).get("hash")
    if not ticket:
        raise RuntimeError(f"login returned no ticket: {raw[:200]}")
    return ticket


def fetch_partial(path, ticket):
    """Fetch a stats 'partial' and return the inner HTML content string."""
    sep = "&" if "?" in path else "?"
    url = f"{API_BASE}/partials/stats/{path}{sep}ticket={ticket}"
    raw = _request(url)
    return html.unescape(json.loads(raw).get("content", ""))


# --- Parsing ---------------------------------------------------------------

def parse_games(schedule_html):
    """Games are embedded as JSON objects inside the schedule partial."""
    games = {}
    for blob in re.findall(r'\{[^{}]*?"game_id":\d+[^{}]*\}', schedule_html):
        try:
            g = json.loads(blob)
        except json.JSONDecodeError:
            continue
        games[g["game_id"]] = g  # dedupe: the partial repeats each game

    out = []
    for g in games.values():
        out.append(
            {
                "game_id": g.get("game_id"),
                "number": (g.get("number") or "").rstrip("0").rstrip(".")
                if g.get("number")
                else g.get("number"),
                "date": g.get("date"),
                "datetime": g.get("datetime"),
                "time": g.get("time"),
                "time_zone_abbr": g.get("time_zone_abbr") or "",
                "status": g.get("status") or "",
                "home_team": g.get("home_team"),
                "home_team_short": g.get("home_team_short"),
                "home_team_id": g.get("home_team_id"),
                "home_score": g.get("home_score"),
                "away_team": g.get("away_team"),
                "away_team_short": g.get("away_team_short"),
                "away_team_id": g.get("away_team_id"),
                "away_score": g.get("away_score"),
                "overtime": g.get("overtime"),
                "shootout": g.get("shootout"),
                "rink": g.get("rink"),
                "facility": g.get("facility"),
                "watch_live_url": g.get("watch_live_url"),
                "external_url": g.get("external_url"),
            }
        )
    out.sort(key=lambda x: (x.get("datetime") or "", x.get("number") or ""))
    return out


_TAG = re.compile(r"<[^>]+>")


def _text(fragment):
    return html.unescape(_TAG.sub("", fragment)).strip()


def parse_standings(standings_html):
    """
    Parse the first standings table (Round Robin / division view — the one the
    site shows by default). Columns: Rk, Team, GP, W, L, T, Pts, GA, GF.
    """
    tbody = re.search(r"<tbody>(.*?)</tbody>", standings_html, re.S)
    if not tbody:
        return []
    rows = re.findall(r"<tr>(.*?)</tr>", tbody.group(1), re.S)
    table = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 9:
            continue
        # team cell has full name + short name links and an id in the href
        team_cell = cells[1]
        links = re.findall(r'<a[^>]*class="team-inline"[^>]*>(.*?)</a>', team_cell, re.S)
        full = _text(links[0]) if links else _text(team_cell)
        short = _text(links[1]) if len(links) > 1 else full
        m = re.search(r"/team/(\d+)", team_cell)
        team_id = int(m.group(1)) if m else None

        def num(i):
            t = _text(cells[i])
            try:
                return int(t)
            except ValueError:
                return t

        table.append(
            {
                "rank": num(0),
                "team": full,
                "team_short": short,
                "team_id": team_id,
                "gp": num(2),
                "w": num(3),
                "l": num(4),
                "t": num(5),
                "pts": num(6),
                "ga": num(7),
                "gf": num(8),
            }
        )
    return table


def is_goodlife(team_id, name):
    if team_id == GOODLIFE_TEAM_ID:
        return True
    return bool(name) and GOODLIFE_NAME_HINT in name.lower()


def main():
    ticket = login()
    schedule_html = fetch_partial(f"schedule/table?division_id={DIVISION_ID}", ticket)
    standings_html = fetch_partial(f"standings/table?division_id={DIVISION_ID}", ticket)

    games = parse_games(schedule_html)
    standings = parse_standings(standings_html)

    if not games:
        raise RuntimeError("No games parsed — aborting so we don't overwrite good data.")

    # Flag GoodLife everywhere so the front end doesn't have to know ids.
    goodlife_full = None
    for s in standings:
        s["is_goodlife"] = is_goodlife(s.get("team_id"), s.get("team"))
        if s["is_goodlife"]:
            goodlife_full = s["team"]
    for g in games:
        g["home_is_goodlife"] = is_goodlife(g.get("home_team_id"), g.get("home_team"))
        g["away_is_goodlife"] = is_goodlife(g.get("away_team_id"), g.get("away_team"))
        g["is_goodlife"] = g["home_is_goodlife"] or g["away_is_goodlife"]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "division_id": DIVISION_ID,
        "division_name": "40 & Over",
        "source_url": f"https://www.narch.com/stats#/{LEAGUE_ID}/schedule?division_id={DIVISION_ID}",
        "goodlife": {
            "team_id": GOODLIFE_TEAM_ID,
            "name": goodlife_full or "Oakland Goodlife - CA",
        },
        "standings": standings,
        "games": games,
    }

    out_path = os.path.abspath(OUT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(
        f"Wrote {out_path}: {len(games)} games, {len(standings)} teams, "
        f"generated_at {payload['generated_at']}"
    )


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
