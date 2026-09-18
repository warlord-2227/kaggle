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

```
main.py                     submission entry point (generated, self-contained)
kaggriculture/agents/       agent implementations
  ranch.py                  livestock -- current best
  crop.py                   melon / wheat / carrot
  farm.py                   goose + wheat (superseded)
  adaptive.py               day-1 opponent read + switch (measured worse; see below)
eval/                       measurement harnesses
  arena.py                  head-to-head win rate, N seeds x 2 sides, parallel
  ladder.py                 vs reference agents, tiers 0-5
  ladder2.py ladder3.py     variant sweeps against the ladder
  meta_bench.py             vs tiers 6-9 (benchmark only, never submitted)
  tune_adversarial.py       parameter tuning scored by win rate, not coins
analysis/                   economics, computed off the simulator's own constants
  model.py                  yields, action budgets, price curves
  objective.py              objective function and strategy comparison
  analyze_replay.py         reads downloaded opponent replays
experiments/                one-off probes, kept as a record of what was tested
submissions/                frozen past submissions, reused as ladder opponents
tools/
  build_submission.py       inlines an agent module into main.py
  watch_rating.sh           polls the leaderboard rating
refagents/                  third-party sparring partners (gitignored)
```

## Building a submission

`main.py` is generated, not hand-edited -- Kaggle takes a single file, so the
agent source lives in `kaggriculture/agents/` and gets inlined:

```bash
python tools/build_submission.py ranch --header tools/header_v6.txt \
  --config "target={'COW': 8, 'SHEEP': 5}, feed_float_days=8, hands=8, land=2, buy_feed=True"
kaggle competitions submit kaggriculture -f main.py -m "..."
```

The build compiles the result, so a syntax error fails locally rather than at
submit time.

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
