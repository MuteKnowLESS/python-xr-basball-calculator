#!/usr/bin/env python3
"""
XR (Extrapolated Runs) Calculator
Usage: python xr.py "Player Name" YEAR
Example: python xr.py "Jose Bautista" 2011
"""

import sys


def calculate_xr(stats: dict) -> float:
    singles = stats.get("H", 0) - stats.get("2B", 0) - stats.get("3B", 0) - stats.get("HR", 0)
    xr = (
        0.59 * singles +
        0.81 * stats.get("2B", 0) +
        1.13 * stats.get("3B", 0) +
        1.53 * stats.get("HR", 0) +
        0.34 * (stats.get("HBP", 0) or 0) +
        0.34 * stats.get("BB", 0) -
        0.09 * (stats.get("IBB", 0) or 0) +
        0.18 * (stats.get("SB", 0) or 0) -
        0.32 * (stats.get("CS", 0) or 0) -
        0.09 * stats.get("AB", 0) -
        0.008 * stats.get("SO", 0) -
        0.37 * (stats.get("GIDP", 0) or stats.get("GDP", 0) or 0) +
        0.37 * (stats.get("SF", 0) or 0) +
        0.04 * (stats.get("SH", 0) or 0)
    )
    return xr


def print_results(name, year, team, stats, xr):
    singles = stats.get("H", 0) - stats.get("2B", 0) - stats.get("3B", 0) - stats.get("HR", 0)
    gidp = stats.get("GIDP", 0) or stats.get("GDP", 0) or 0
    print(f"\n{'='*45}")
    print(f"  Player : {name}")
    print(f"  Season : {year}")
    print(f"  Team   : {team}")
    print(f"{'='*45}")
    print(f"  AB     : {int(stats.get('AB', 0))}")
    print(f"  1B     : {int(singles)}")
    print(f"  2B     : {int(stats.get('2B', 0))}")
    print(f"  3B     : {int(stats.get('3B', 0))}")
    print(f"  HR     : {int(stats.get('HR', 0))}")
    print(f"  BB     : {int(stats.get('BB', 0))}")
    print(f"  IBB    : {int(stats.get('IBB', 0) or 0)}")
    print(f"  HBP    : {int(stats.get('HBP', 0) or 0)}")
    print(f"  SO     : {int(stats.get('SO', 0))}")
    print(f"  SB     : {int(stats.get('SB', 0) or 0)}")
    print(f"  CS     : {int(stats.get('CS', 0) or 0)}")
    print(f"  GIDP   : {int(gidp)}")
    print(f"  SF     : {int(stats.get('SF', 0) or 0)}")
    print(f"  SH     : {int(stats.get('SH', 0) or 0)}")
    print(f"{'='*45}")
    print(f"  XR     : {xr:.1f}")
    print(f"{'='*45}\n")


# ── Strategy 1: Baseball Reference via pybaseball ──────────────────────────
def try_bbref(player_name: str, year: int):
    from pybaseball import batting_stats_bref, playerid_lookup
    import pandas as pd

    data = batting_stats_bref(year)          # pulls the full BR standard batting table
    data["_name_lower"] = data["Name"].str.lower()
    name_lower = player_name.lower()

    matches = data[data["_name_lower"] == name_lower]
    if matches.empty:
        last = player_name.split()[-1].lower()
        matches = data[data["_name_lower"].str.contains(last)]
    if matches.empty:
        return None

    row = matches.iloc[0]
    stats = row.to_dict()
    team = stats.get("Tm", "N/A")
    return row["Name"], team, stats


# ── Strategy 2: MLB Stats API (no key required) ────────────────────────────
def try_mlb_api(player_name: str, year: int):
    import requests

    # Search for player
    search_url = "https://statsapi.mlb.com/api/v1/people/search"
    r = requests.get(search_url, params={"names": player_name, "sportId": 1},
                     timeout=10)
    r.raise_for_status()
    people = r.json().get("people", [])
    if not people:
        return None

    # Try to find a close name match
    name_lower = player_name.lower()
    person = next(
        (p for p in people if p.get("fullName", "").lower() == name_lower),
        people[0]
    )
    pid = person["id"]
    full_name = person["fullName"]

    # Fetch batting stats for the season
    stats_url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats"
    r = requests.get(stats_url, params={
        "stats": "season",
        "season": year,
        "group": "hitting",
        "sportId": 1
    }, timeout=10)
    r.raise_for_status()

    splits = r.json().get("stats", [{}])[0].get("splits", [])
    if not splits:
        return None

    # If multiple teams (traded), aggregate
    totals = {}
    team = "TOT"
    for split in splits:
        s = split.get("stat", {})
        team = split.get("team", {}).get("abbreviation", "N/A")
        for k, v in s.items():
            try:
                totals[k] = totals.get(k, 0) + int(v)
            except (ValueError, TypeError):
                totals[k] = v

    if len(splits) > 1:
        team = "TOT"

    # Map MLB API field names → our stat names
    field_map = {
        "atBats": "AB", "hits": "H", "doubles": "2B", "triples": "3B",
        "homeRuns": "HR", "baseOnBalls": "BB", "intentionalWalks": "IBB",
        "hitByPitch": "HBP", "strikeOuts": "SO", "stolenBases": "SB",
        "caughtStealing": "CS", "groundIntoDoublePlay": "GIDP",
        "sacFlies": "SF", "sacBunts": "SH",
    }
    stats = {v: totals.get(k, 0) for k, v in field_map.items()}
    return full_name, team, stats


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python xr.py \"Player Name\" YEAR")
        print("Example: python xr.py \"Jose Bautista\" 2011")
        sys.exit(1)

    # Accept "Name, Year" as a single arg or two separate args
    if len(sys.argv) == 2 and "," in sys.argv[1]:
        parts = sys.argv[1].rsplit(",", 1)
        player_name = parts[0].strip()
        year = int(parts[1].strip())
    else:
        player_name = sys.argv[1].strip()
        year = int(sys.argv[2].strip())

    print(f"Looking up stats for {player_name} ({year})...")

    result = None

    # --- Try Baseball Reference first ---
    try:
        from pybaseball import batting_stats_bref
        print("Trying Baseball Reference...")
        result = try_bbref(player_name, year)
        if result:
            print("Found via Baseball Reference.")
    except Exception as e:
        print(f"  Baseball Reference failed: {e}")

    # --- Fall back to MLB Stats API ---
    if not result:
        try:
            import requests
            print("Trying MLB Stats API...")
            result = try_mlb_api(player_name, year)
            if result:
                print("Found via MLB Stats API.")
        except ImportError:
            print("  requests not installed. Run: pip install requests")
        except Exception as e:
            print(f"  MLB Stats API failed: {e}")

    if not result:
        print(f"\nError: Could not find stats for '{player_name}' in {year}.")
        print("Tips:")
        print("  - Check spelling (e.g. 'Jose Bautista' not 'Jose Batista')")
        print("  - The player may not have batted that season")
        sys.exit(1)

    name, team, stats = result
    xr = calculate_xr(stats)
    print_results(name, year, team, stats, xr)


if __name__ == "__main__":
    main()
