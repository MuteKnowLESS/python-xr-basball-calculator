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


def print_results(name, year, team, stats, xr, position=None, pitcher_mode=False):
    singles = stats.get("H", 0) - stats.get("2B", 0) - stats.get("3B", 0) - stats.get("HR", 0)
    gidp = stats.get("GIDP", 0) or stats.get("GDP", 0) or 0
    pos_str = f" ({position})" if position else ""
    print(f"\n{'='*45}")
    print(f"  Player : {name}{pos_str}")
    print(f"  Season : {year}")
    print(f"  Team   : {team}")
    if pitcher_mode:
        print(f"  Mode   : Pitcher — stats are vs. batters faced")
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
    if pitcher_mode:
        print(f"  XR     : {xr:.1f}  (runs allowed estimate)")
    else:
        print(f"  XR     : {xr:.1f}")
    print(f"{'='*45}\n")


# ── MLB Stats API ──────────────────────────────────────────────────────────
MLB_HITTING_MAP = {
    "atBats": "AB", "hits": "H", "doubles": "2B", "triples": "3B",
    "homeRuns": "HR", "baseOnBalls": "BB", "intentionalWalks": "IBB",
    "hitByPitch": "HBP", "strikeOuts": "SO", "stolenBases": "SB",
    "caughtStealing": "CS", "groundIntoDoublePlay": "GIDP",
    "sacFlies": "SF", "sacBunts": "SH",
}

# Pitching splits use different field names for the same concepts
MLB_PITCHING_MAP = {
    "atBats": "AB", "hits": "H", "doubles": "2B", "triples": "3B",
    "homeRuns": "HR", "baseOnBalls": "BB", "intentionalWalks": "IBB",
    "hitBatsmen": "HBP", "strikeOuts": "SO", "stolenBases": "SB",
    "caughtStealing": "CS", "groundIntoDoublePlay": "GIDP",
    "sacFlies": "SF", "sacBunts": "SH",
}


def mlb_api_get(url, params=None):
    import requests
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def team_from_split(split):
    """Extract team name or abbreviation from a split dict."""
    team = split.get("team", {})
    # Prefer abbreviation, fall back to full name
    return team.get("abbreviation") or team.get("name") or "N/A"


def aggregate_splits(splits, field_map):
    """Sum numeric stat fields across splits (handles traded players)."""
    totals = {}
    teams = []
    for split in splits:
        teams.append(team_from_split(split))
        for k, v in split.get("stat", {}).items():
            try:
                totals[k] = totals.get(k, 0) + int(v)
            except (ValueError, TypeError):
                pass
    team = "TOT" if len(splits) > 1 else teams[0]
    stats = {v: totals.get(k, 0) for k, v in field_map.items()}
    return team, stats


def try_mlb_api(player_name: str, year: int):
    # 1. Search
    data = mlb_api_get("https://statsapi.mlb.com/api/v1/people/search",
                        params={"names": player_name, "sportId": 1})
    people = data.get("people", [])
    if not people:
        return None

    name_lower = player_name.lower()
    person = next(
        (p for p in people if p.get("fullName", "").lower() == name_lower),
        people[0]
    )
    pid = person["id"]
    full_name = person["fullName"]

    # 2. Player meta (position)
    meta = mlb_api_get(f"https://statsapi.mlb.com/api/v1/people/{pid}")
    player_meta = meta.get("people", [{}])[0]
    position = player_meta.get("primaryPosition", {}).get("abbreviation")

    # 3. Try hitting stats
    hitting_data = mlb_api_get(
        f"https://statsapi.mlb.com/api/v1/people/{pid}/stats",
        params={"stats": "season", "season": year, "group": "hitting", "sportId": 1}
    )
    hitting_splits = hitting_data.get("stats", [{}])[0].get("splits", [])

    if hitting_splits:
        team, stats = aggregate_splits(hitting_splits, MLB_HITTING_MAP)
        return full_name, team, stats, position, False

    # 4. Fall back to pitching splits (stats vs. batters faced)
    pitching_data = mlb_api_get(
        f"https://statsapi.mlb.com/api/v1/people/{pid}/stats",
        params={"stats": "season", "season": year, "group": "pitching", "sportId": 1}
    )
    pitching_splits = pitching_data.get("stats", [{}])[0].get("splits", [])

    if pitching_splits:
        print(f"\nNote: {full_name} is a pitcher with no plate appearances.")
        print("Using stats vs. batters faced — XR will estimate runs allowed.\n")
        team, stats = aggregate_splits(pitching_splits, MLB_PITCHING_MAP)
        return full_name, team, stats, position, True

    print(f"\nNote: Found {full_name} but no MLB stats for {year}.")
    print("They may have been in the minors, on IL, or not on a roster.")
    return None


# ── Baseball Reference via pybaseball ─────────────────────────────────────
def try_bbref(player_name: str, year: int):
    from pybaseball import batting_stats_bref

    data = batting_stats_bref(year)
    data["_name_lower"] = data["Name"].str.lower()
    name_lower = player_name.lower()

    matches = data[data["_name_lower"] == name_lower]
    if matches.empty:
        last = player_name.split()[-1].lower()
        matches = data[data["_name_lower"].str.contains(last, na=False)]
    if matches.empty:
        return None

    row = matches.iloc[0]
    stats = row.to_dict()
    team = stats.get("Tm", "N/A")
    return row["Name"], team, stats, None, False


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python xr.py \"Player Name\" YEAR")
        print("Example: python xr.py \"Jose Bautista\" 2011")
        sys.exit(1)

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
        from pybaseball import batting_stats_bref  # noqa: F401
        print("Trying Baseball Reference...")
        result = try_bbref(player_name, year)
        if result:
            print("Found via Baseball Reference.")
    except Exception as e:
        print(f"  Baseball Reference failed: {e}")

    # --- Fall back to MLB Stats API ---
    if not result:
        try:
            import requests  # noqa: F401
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

    name, team, stats, position, pitcher_mode = result
    xr = calculate_xr(stats)
    print_results(name, year, team, stats, xr, position, pitcher_mode)


if __name__ == "__main__":
    main()
