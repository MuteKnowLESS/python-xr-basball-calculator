#!/usr/bin/env python3
"""
Best Hitters by XR — 2025 Season
Usage: python best_hitters.py [--top N] [--min-pa N] [--position POS]

Examples:
  python best_hitters.py
  python best_hitters.py --top 20
  python best_hitters.py --top 10 --position SS
  python best_hitters.py --min-pa 300
"""

import sys
import argparse


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
        0.37 * (stats.get("GIDP", 0) or 0) +
        0.37 * (stats.get("SF", 0) or 0) +
        0.04 * (stats.get("SH", 0) or 0)
    )
    return xr


def pa_from_stats(stats: dict) -> int:
    pa = stats.get("PA", 0)
    if pa:
        return int(pa)
    return int(
        stats.get("AB", 0) +
        stats.get("BB", 0) +
        (stats.get("HBP", 0) or 0) +
        (stats.get("SF", 0) or 0) +
        (stats.get("SH", 0) or 0)
    )


MLB_HITTING_MAP = {
    "atBats": "AB", "hits": "H", "doubles": "2B", "triples": "3B",
    "homeRuns": "HR", "baseOnBalls": "BB", "intentionalWalks": "IBB",
    "hitByPitch": "HBP", "strikeOuts": "SO", "stolenBases": "SB",
    "caughtStealing": "CS", "groundIntoDoublePlay": "GIDP",
    "sacFlies": "SF", "sacBunts": "SH",
    "gamesPlayed": "G", "runs": "R", "plateAppearances": "PA",
}


def mlb_api_get(url, params=None):
    import requests
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_all_hitters(year: int, min_pa: int, position_filter: str = None):
    """Fetch all batters for a season from the MLB Stats API."""
    import requests

    print(f"Fetching all MLB hitters for {year}...")

    # Pull the full season batting leaderboard
    # sportId=1 = MLB, limit high enough to get everyone
    url = "https://statsapi.mlb.com/api/v1/stats"
    params = {
        "stats": "season",
        "season": year,
        "group": "hitting",
        "sportId": 1,
        "limit": 2000,
        "offset": 0,
        "sortStat": "plateAppearances",
        "order": "desc",
    }

    data = mlb_api_get(url, params)
    splits = data.get("stats", [{}])[0].get("splits", [])
    print(f"  Retrieved {len(splits)} player-seasons.")

    results = []
    for split in splits:
        s = split.get("stat", {})
        player = split.get("player", {})
        team = split.get("team", {})

        name = player.get("fullName", "Unknown")
        team_name = team.get("name", "N/A")
        pid = player.get("id")

        # Map stats
        stats = {}
        for api_key, our_key in MLB_HITTING_MAP.items():
            try:
                stats[our_key] = int(s.get(api_key, 0) or 0)
            except (ValueError, TypeError):
                stats[our_key] = 0

        pa = pa_from_stats(stats)
        if pa < min_pa:
            continue

        xr = calculate_xr(stats)
        xr_per_pa = xr / pa if pa > 0 else 0

        results.append({
            "name": name,
            "team": team_name,
            "pid": pid,
            "stats": stats,
            "xr": xr,
            "pa": pa,
            "xr_per_pa": xr_per_pa,
        })

    # Optionally filter by position
    if position_filter:
        print(f"  Fetching positions for filtered results...")
        filtered = []
        for p in results:
            try:
                meta = mlb_api_get(f"https://statsapi.mlb.com/api/v1/people/{p['pid']}")
                pos = meta.get("people", [{}])[0].get("primaryPosition", {}).get("abbreviation", "")
                if pos.upper() == position_filter.upper():
                    p["position"] = pos
                    filtered.append(p)
            except Exception:
                pass
        results = filtered
    else:
        for p in results:
            p["position"] = ""

    return results


def print_leaderboard(results, top_n, year, min_pa, sort_by, position_filter):
    results_sorted = sorted(results, key=lambda x: x[sort_by], reverse=True)[:top_n]

    pos_str = f" — {position_filter.upper()}" if position_filter else ""
    sort_label = "XR/PA" if sort_by == "xr_per_pa" else "XR"
    print(f"\n{'='*72}")
    print(f"  TOP {top_n} HITTERS BY {sort_label} — {year}{pos_str}  (min {min_pa} PA)")
    print(f"{'='*72}")
    print(f"  {'#':<4} {'Name':<24} {'Team':<22} {'Pos':<5} {'G':>4} {'PA':>5} {'HR':>4} {'XR':>7} {'XR/PA':>7}")
    print(f"  {'-'*68}")

    for i, p in enumerate(results_sorted, 1):
        s = p["stats"]
        pos = p.get("position", "")
        print(
            f"  {i:<4} {p['name']:<24} {p['team']:<22} {pos:<5} "
            f"{s.get('G', 0):>4} {p['pa']:>5} {s.get('HR', 0):>4} "
            f"{p['xr']:>7.1f} {p['xr_per_pa']:>7.4f}"
        )

    print(f"{'='*72}\n")


def main():
    parser = argparse.ArgumentParser(description="Best MLB hitters by XR")
    parser.add_argument("--top", type=int, default=25, help="Number of players to show (default: 25)")
    parser.add_argument("--min-pa", type=int, default=200, help="Minimum plate appearances (default: 200)")
    parser.add_argument("--year", type=int, default=2025, help="Season year (default: 2025)")
    parser.add_argument("--position", type=str, default=None, help="Filter by position (e.g. SS, 1B, OF, DH)")
    parser.add_argument("--rate", action="store_true", help="Sort by XR/PA rate instead of raw XR")
    args = parser.parse_args()

    sort_by = "xr_per_pa" if args.rate else "xr"

    try:
        results = fetch_all_hitters(args.year, args.min_pa, args.position)
    except ImportError:
        print("Error: requests not installed. Run: pip install requests")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    if not results:
        print("No results found. Try lowering --min-pa.")
        sys.exit(1)

    print_leaderboard(results, args.top, args.year, args.min_pa, sort_by, args.position)


if __name__ == "__main__":
    main()
