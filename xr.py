#!/usr/bin/env python3
"""
XR (Extrapolated Runs) Calculator
Usage: python xr.py "Player Name" YEAR
       python xr.py "Player Name" --project

Examples:
  python xr.py "Gunnar Henderson" 2025
  python xr.py "Gunnar Henderson" --project
"""

import sys

# League-average XR for a full season (~550 AB), used for regression to mean
LEAGUE_AVG_XR = 65.0
# Dollar value per WAR (current market)
DOLLARS_PER_WAR = 8_500_000
# XR runs per WAR
XR_PER_WAR = 10.0
# Standard full-season PA for projection
FULL_SEASON_PA = 600


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


def pa_from_stats(stats: dict) -> int:
    """Estimate plate appearances from available stats."""
    pa = stats.get("PA", 0)
    if pa:
        return int(pa)
    # PA = AB + BB + HBP + SF + SH
    return int(
        stats.get("AB", 0) +
        stats.get("BB", 0) +
        (stats.get("HBP", 0) or 0) +
        (stats.get("SF", 0) or 0) +
        (stats.get("SH", 0) or 0)
    )


def age_adjustment(age: int) -> float:
    """
    Simple age curve: peak ~27, +2 XR/yr climbing to peak, -3 XR/yr declining after.
    Returns the adjustment to apply to the projected XR.
    """
    peak_age = 27
    if age is None:
        return 0.0
    if age < peak_age:
        return min((peak_age - age) * 2.0, 6.0)   # cap improvement at +6
    else:
        return -min((age - peak_age) * 3.0, 20.0)  # cap decline at -20


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
    print(f"  G      : {int(stats.get('G', 0))}")
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
        print(f"  R      : {int(stats.get('R', 0))}")
        print(f"  XR     : {xr:.1f}")
    print(f"{'='*45}\n")


def print_projection(name, position, seasons: list, projected_xr: float,
                     age: int, age_adj: float, proj_pa: int):
    """
    seasons: list of (year, xr, pa, weight) tuples, newest first
    """
    pos_str = f" ({position})" if position else ""
    next_year = max(s[0] for s in seasons) + 1
    offensive_war = projected_xr / XR_PER_WAR
    dollar_value = offensive_war * DOLLARS_PER_WAR

    print(f"\n{'='*51}")
    print(f"  PROJECTION — {name}{pos_str}")
    print(f"{'='*51}")
    print(f"  {'Year':<8} {'XR':>6}  {'PA':>5}  {'Weight':>6}")
    print(f"  {'-'*35}")
    for year, xr, pa, w in seasons:
        avail = "(partial)" if pa < 400 else ""
        print(f"  {year:<8} {xr:>6.1f}  {pa:>5}  {w:>5}x  {avail}")
    print(f"  {'-'*35}")
    print(f"  Weighted XR/PA baseline  : {projected_xr + age_adj*-1:>6.1f}  (before age adj)")
    if age and age_adj != 0:
        direction = "+" if age_adj >= 0 else ""
        print(f"  Age adjustment ({age} yrs)   : {direction}{age_adj:.1f}")
    print(f"  Regression to mean (~20%): included")
    print(f"{'='*51}")
    print(f"  Projected {next_year} XR         : {projected_xr:>6.1f}")
    print(f"  Projected {next_year} PA         : {proj_pa:>6}")
    print(f"  Offensive WAR estimate   : {offensive_war:>6.1f}")
    print(f"  Est. offensive value     : ${dollar_value:>10,.0f}")
    print(f"{'='*51}")
    print()
    print("  Notes:")
    print("  - XR/PA rate weighted: 3x most recent, 2x prior, 1x oldest")
    print("  - Regressed 20% toward league average to reduce noise")
    print("  - Projected PA based on average of available seasons")
    print("  - Age curve: +2 XR/yr below peak (27), -3 XR/yr above peak")
    print("  - Offensive WAR only; does not include fielding or baserunning")
    print(f"  - Dollar value at ${DOLLARS_PER_WAR/1e6:.1f}M/WAR ({XR_PER_WAR:.0f} XR = 1 oWAR)")
    print(f"{'='*51}\n")


# ── MLB Stats API ──────────────────────────────────────────────────────────
MLB_HITTING_MAP = {
    "atBats": "AB", "hits": "H", "doubles": "2B", "triples": "3B",
    "homeRuns": "HR", "baseOnBalls": "BB", "intentionalWalks": "IBB",
    "hitByPitch": "HBP", "strikeOuts": "SO", "stolenBases": "SB",
    "caughtStealing": "CS", "groundIntoDoublePlay": "GIDP",
    "sacFlies": "SF", "sacBunts": "SH",
    "gamesPlayed": "G", "runs": "R", "plateAppearances": "PA",
}

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
    team = split.get("team", {})
    return team.get("abbreviation") or team.get("name") or "N/A"


def aggregate_splits(splits, field_map):
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


def get_player_id(player_name: str):
    """Return (pid, full_name, position, birth_date) from MLB API."""
    data = mlb_api_get("https://statsapi.mlb.com/api/v1/people/search",
                        params={"names": player_name, "sportId": 1})
    people = data.get("people", [])
    if not people:
        return None, None, None, None

    name_lower = player_name.lower()
    person = next(
        (p for p in people if p.get("fullName", "").lower() == name_lower),
        people[0]
    )
    pid = person["id"]
    full_name = person["fullName"]

    meta = mlb_api_get(f"https://statsapi.mlb.com/api/v1/people/{pid}")
    player_meta = meta.get("people", [{}])[0]
    position = player_meta.get("primaryPosition", {}).get("abbreviation")
    birth_date = player_meta.get("birthDate")  # "YYYY-MM-DD"
    return pid, full_name, position, birth_date


def get_hitting_stats_for_year(pid: int, year: int):
    """Return (team, stats) or None if no hitting data."""
    hitting_data = mlb_api_get(
        f"https://statsapi.mlb.com/api/v1/people/{pid}/stats",
        params={"stats": "season", "season": year, "group": "hitting", "sportId": 1}
    )
    splits = hitting_data.get("stats", [{}])[0].get("splits", [])
    if not splits:
        return None
    return aggregate_splits(splits, MLB_HITTING_MAP)


def try_mlb_api(player_name: str, year: int):
    pid, full_name, position, _ = get_player_id(player_name)
    if pid is None:
        return None

    result = get_hitting_stats_for_year(pid, year)
    if result:
        team, stats = result
        return full_name, team, stats, position, False

    # Fall back to pitching
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


def try_mlb_api_project(player_name: str, base_year: int):
    """Fetch up to 3 seasons ending at base_year and return projection."""
    import datetime

    pid, full_name, position, birth_date = get_player_id(player_name)
    if pid is None:
        return None

    # Determine age in the projection year
    age = None
    if birth_date:
        try:
            by = int(birth_date[:4])
            age = (base_year + 1) - by
        except Exception:
            pass

    weights = [3, 2, 1]
    years_to_try = [base_year, base_year - 1, base_year - 2]
    seasons = []  # (year, xr, pa, weight)

    for year, w in zip(years_to_try, weights):
        result = get_hitting_stats_for_year(pid, year)
        if result:
            _, stats = result
            xr = calculate_xr(stats)
            pa = pa_from_stats(stats)
            if pa > 0:
                seasons.append((year, xr, pa, w))

    if not seasons:
        print(f"\nNo hitting data found for {full_name} in {years_to_try}.")
        return None

    # Weighted XR/PA rate
    total_weight = sum(w for _, _, _, w in seasons)
    weighted_xr_per_pa = sum((xr / pa) * w for _, xr, pa, w in seasons) / total_weight

    # Projected PA = average PA across available seasons
    avg_pa = sum(pa for _, _, pa, _ in seasons) / len(seasons)
    proj_pa = min(int(avg_pa), FULL_SEASON_PA)

    # Raw projected XR
    raw_xr = weighted_xr_per_pa * proj_pa

    # Regress 20% toward league average
    league_avg_rate = LEAGUE_AVG_XR / FULL_SEASON_PA
    regressed_xr = raw_xr * 0.80 + (league_avg_rate * proj_pa) * 0.20

    # Age adjustment
    adj = age_adjustment(age) if age else 0.0
    projected_xr = regressed_xr + adj

    print_projection(full_name, position, seasons, projected_xr, age, adj, proj_pa)
    return True


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
    stats["GIDP"] = stats.get("GDP", 0)
    team = stats.get("Tm", "N/A")
    return row["Name"], team, stats, None, False


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python xr.py \"Player Name\" YEAR")
        print("  python xr.py \"Player Name\" --project [YEAR]")
        print()
        print("Examples:")
        print("  python xr.py \"Gunnar Henderson\" 2025")
        print("  python xr.py \"Gunnar Henderson\" --project")
        print("  python xr.py \"Gunnar Henderson\" --project 2024  (project from a past year)")
        sys.exit(1)

    # Parse args
    project_mode = "--project" in sys.argv

    if project_mode:
        sys.argv.remove("--project")
        player_name = sys.argv[1].strip()
        # Optional base year (defaults to current season)
        base_year = int(sys.argv[2].strip()) if len(sys.argv) > 2 else 2025
        print(f"Projecting {player_name} for {base_year + 1} using {base_year} and prior seasons...")
        try:
            result = try_mlb_api_project(player_name, base_year)
            if not result:
                print("Could not generate projection.")
                sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        return

    # Normal single-season mode
    if len(sys.argv) == 2 and "," in sys.argv[1]:
        parts = sys.argv[1].rsplit(",", 1)
        player_name = parts[0].strip()
        year = int(parts[1].strip())
    else:
        player_name = sys.argv[1].strip()
        year = int(sys.argv[2].strip())

    print(f"Looking up stats for {player_name} ({year})...")

    result = None

    try:
        from pybaseball import batting_stats_bref  # noqa: F401
        print("Trying Baseball Reference...")
        result = try_bbref(player_name, year)
        if result:
            print("Found via Baseball Reference.")
    except Exception as e:
        print(f"  Baseball Reference failed: {e}")

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
