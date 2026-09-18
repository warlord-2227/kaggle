# Kaggriculture

Agent for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture)
simulation competition. Two players farm for 720 turns; most coins wins.

## Current agent

`main.py` — livestock with **purchased** feed: 8 cows, 5 sheep, 8 hands,
2 extra quadrants.

| Measure | Value |
| --- | --- |
| Median final bank (vs `pass`) | 37,151 (worst case 36,255) |
| Reference ladder, tiers 1-5 | 30/30 |
| vs tier-5 Rancher Rita | 6W-0L |

## Setup

```bash
uv venv --python 3.12 .venv && . .venv/bin/activate
uv pip install -U kaggle-environments kaggle
kaggle datasets download raykkretzschmar/kaggriculture-reference-agents \
  -p refagents --unzip          # sparring partners, not redistributed here
```

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | Current submission |
| `ranch.py` | Livestock farm (parameterised) |
| `crop.py` | Melon/wheat/carrot farm |
| `farm.py` | Earlier goose+wheat farm |
| `adaptive.py` | Day-1 opponent read + strategy switch (measured worse; kept for the read) |
| `arena.py` | Head-to-head win rate, N seeds x 2 sides, parallel |
| `ladder*.py` | Runs against the reference agents |
| `model.py`, `objective.py` | Closed-form economics off the simulator's own constants |
| `probe.py`, `exp_*.py` | Single-mechanic experiments |
| `analyze_replay.py` | Reads downloaded opponent replays |
| `v2_*.py` … `v5_*.py` | Frozen prior submissions, kept as ladder opponents |

## What the measurements say

- **Buy feed, don't grow it.** Growing is cheaper in coins but spends tiles and
  actions on a 20-coin staple; buying frees every tile for 240-267 coin/tile/day
  livestock. Worth +26% and a much tighter floor.
- **Deny, don't dodge.** Scoring is relative, so suppressing the opponent counts
  as much as earning. Avoiding Rita's market earned us *more* and lost the game
  (she scored 53,387); contesting it cost us ~1,600 and cost her ~40,000.
- **Feed float must cover the herd after the purchase.** Sizing it on the
  current herd makes it zero on day 0 — animals get bought that cannot be fed
  and the herd starves by day 2.
- **Market orders fire per turn, not per day.** The single most repeated bug:
  an unguarded rule buys ~288 units/day up a rising price curve.
- **Liquidate from day 28.** Inventory is worth zero at turn 720.
- **Test against real agents.** Every sweep run against `pass` misled us; the
  strategy only got fixed after reading opponent replays.

## Open

Remaining gap to the top is the **market layer**, not production: the reference
dataset notes that tiers 6-9 share one field plan and differ only in when they
sell, and that alone spreads them by thousands. Ours uses fixed chunk sizes and
fixed ordering with no timing.
