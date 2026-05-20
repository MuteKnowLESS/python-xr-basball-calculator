caclulates the XR of baseball players given a name and season year. example input: python xr.py "John Smith" 2024  (DISCLAIMER: THIS CODE WAS PARTIALLY GENRENATED USING CLAUDE CODE)

Data from pybaseball and the MLB api

## xr.py

this script takes a player name and year and gives an out put of their statistics. a --prediction <optional: year> can be used to predict the runs and value of the player for the current year or the year after the year provided when running the program

## best_hitters.py

this script can be used to make a list of players based on their stats.

```bash
# Top 25 hitters by raw XR (default)
python best_hitters.py

# Top 10 by XR rate (better for comparing part-time vs full-time players)
python best_hitters.py --top 10 --rate

# Filter by position
python best_hitters.py --position SS
python best_hitters.py --position 1B --top 10

# Lower the minimum PA threshold (e.g. to include part-time players)
python best_hitters.py --min-pa 100

# Different year
python best_hitters.py --year 2023
```
