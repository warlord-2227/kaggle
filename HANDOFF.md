# Kaggriculture — session handoff (2026-09-22, 12:10 local / 00:10 UTC)

Competition: https://www.kaggle.com/competitions/kaggriculture (2-player farming sim, 720 turns, most coins wins).
Deadline 2026-09-30. 5 submissions per **UTC** day (local = UTC+12, quota resets 12:00 local). Only the latest 2
submissions play. Account: IWA_setu (user `sdcarson`), token in `~/.kaggle/access_token`.
Doc for the user (tabs Plan / Objective model / …): https://claude.ai/code/artifact/9249d30d-43a8-49ba-9de4-53a99f7aced3
Repo: `/home/iwa/working/kaggle`, branch `agent/livestock-v6`, last pushed commit `23a6039` (v22). **Uncommitted since:
market.py changes (opp-aware Cournot, NPV herd mode, geese floor, dynamic fert reserve…), eval/trace_agent.py, evolve_market.py
fitness changes, v23 files, replay pools. The user asked for no commits on the evening of 09-21; ask before committing.**

## Where we stand

| Sub | id | Agent | Rating (games) |
|---|---|---|---|
| v17 | 56404036 | grove (fixed strawberry plan + labour auction) | 659 (32) — inactive |
| v20 | 56413854 | grove, search genome | 640 (32) — inactive |
| v21 | 56420053 | **market** (demand-driven), search round 1 | 652 (36) — inactive |
| v22 | 56423303 | market, search round 2 (vs v21) | **709 (35)** — active |
| v23 | 56446174 | market, gen-53 genome tuned vs replayed real opponents | submitted 00:02 UTC 09-22 — active, no rating yet |

Ladder scale: 9,724 teams, median 771. 1000 ≈ rank 4,050 (top 42%), 1500 ≈ top 27%, bronze (rank 941) ≈ 2,450, top-10 ≈ 3,000.
Rank-1 "DSM" (sub 56401245): 115–3, median 110k vs 3000-rated peers.

## Agents (kaggriculture/agents/)

- `market.py` — current line. Demand-driven: each unlocked town shop buys 6 units/day of each product it lists (12 if
  single-product), town centre 1/day, nothing buys melon/fertilizer; product lines (cows/sheep/geese/strawberry/wheat/
  carrot/tomato) sized to that drain × knobs. Labour = grove's coin-priced auction (jobs valued in coins, greedy match by
  value/(1+dist), stay-and-finish on a tile, bundled tile values, deliver-to-shed job, idle = PASS). Opening: cows+3 sheep,
  10 wheat, melon lump on day 10; herd bought whenever cash lands; carrot/wheat sprint late. Knobs in `DEFAULT`.
  Flags that exist but are OFF by default and measured negative: `herd_npv` (NPV herd rule), `zone_mode="kmeans"`,
  `match="job"/"optimal"`, `commit`, `harvest_full`, `opp_weight` (Cournot subtraction; search sets ~0.1–0.2).
- `grove.py` — previous line (v17–v20). `ranch.py` (v6–v16), `schedule.py` (dead end), `crop.py`, `farm.py`.
- Build a submission: `.venv/bin/python tools/build_submission.py market --header tools/header_vN.txt --config "$(cat cfg.txt)"`
  where cfg.txt is `k=v, k=v…` from the genome (see how v23 was built in the transcript / memory). Snapshots in `submissions/`.
- Submit: `.venv/bin/kaggle competitions submit -c kaggriculture -f submissions/vN.py -m "…"`. A 400 = quota exhausted.
  Scheduled submit pattern: `scratchpad/submit_v23.sh` (waits for UTC day rollover, retries).

## Evaluation (the important part)

- `eval/fair_env.py` — patches the shop-draw RNG so two agents on the same seed get the same shops (use for agent-vs-agent
  and vs pass). **Do NOT use with replayed traces.**
- `eval/trace_agent.py` — replays a recorded ladder opponent open-loop. `pool(min_rating, folder)` lists
  `replays/pool` (50 opponents rated 640–1033 that beat us; 34 rated 700+) or `replays/top` (25 opponents rated 2938–3197
  from rank-1's games). Each trace **must run on its own seed** (`seed_of(path)` = replay `info.seed`) in the **real env**.
  Fidelity is decent (e.g. the 1033 opponent replays 125k vs 127k recorded) but traces don't react to us.
- Standard verification of a candidate genome (what gated v23): (1) full pools on native seeds: ladder 34 + top 25;
  (2) fair-env: vs previous candidate (6–8 seeds), vs pass (4), glut seeds 9002/9006 (no strawberry shop → price 128→16).
  Reference numbers, gen-53/v23: ladder 29/34 (+12.7k), top 9/25 (−3.8k), held-out(<700) 15/16, 146k vs pass, 110k glut.
  v22: ladder 13/34 (−3.4k).
- Episode API (no auth): `POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes {"submissionId": N}`;
  replays: `curl -L https://www.kaggleusercontent.com/episodes/<id>.json`. Team → submission id: leaderboard page,
  "View episodes" button → URL `?submissionId=`. Leaderboard CSV: `kaggle competitions leaderboard --download`.

## Search

- `experiments/evolve_market.py` — (μ+λ)=(4+12), ~55 knobs incl. the new ones. Fitness = margin vs 8 rotating traces from
  `TRACE_POOL` (34 ladder + 25 top) + one pass game, 2 seeds (trace seeds are native). Log
  `experiments/evolve_market_log.jsonl`, best `experiments/evolve_market_best.json`. Elites seeded from v23/v22 genomes.
  Run: `(. .venv/bin/activate && nohup python experiments/evolve_market.py <rngseed> > scratchpad/evolve_marketN.log 2>&1 &)`.
  A run was alive at handoff (arg `8`, log `evolve_market8.log`, gen ~35). Its elite did NOT beat gen-53 on the full pools.
- Genomes: `experiments/v21_genome.json`, `v22_genome.json`, `v23_genome.json` (= gen-53), candidates `cand_*.json`.
- `experiments/evolve_grove.py` / `evolve_ranch.py` — older lines.

## Findings that matter (all measured)

1. Objective mismatch was the core error: coins vs pass ≠ ladder rating. Optimizing vs replayed real opponents lifted the
   pool win-rate 38% → 85% (v22 → gen-53) with no change in code.
2. Executor bugs found and fixed on the way: market cap of 10 orders/turn silently limited hires to 10 (hires now spill to
   hours 1–2); FEED/CARE underpriced (unfed animals → no milk); one animal's feed/care/collect split across units (stay-and-
   finish); produce sold only from the shed → deliver job; feed re-bought while carried.
3. Mechanics from the engine: plant dies after 2 unwatered days; strawberry +1 unit per 2 days from age 10 (×2 if fertilized
   AND watered that night), 4 productions then dies; melon yield accrues per watered day at ages 6–12 (+2 fertilized);
   animals: base 1 per interval, +1 per fed&cared day, unfed production day forfeits the bonus, 2 unfed days = escape;
   hires cost Fibonacci per hand per day; shops unlock days 4,6,10,12,16,20,24 from 8 types.
4. Top tier vs v23 (25 games): we already match them in output (94k vs 98k); they win by consistency. Our wins have 12–13 cows
   by day 12, our losses 4–6; they wind strawberries down from day 18 into wheat/carrot/tomato, keep 2–3 geese, sell
   476 wheat / 122 eggs / 113 carrots / 89 tomatoes to our 102/0/18/0.
5. Rejected (worse on the pools): copying the top structure by hand, hardcoded herd floors, NPV herd rule (both variants),
   Cournot withdrawal (helps opponents), k-means territories, job-centric/Hungarian matching, commitment, more hands, 4th quadrant.
   Everything hand-set lost to search-tuned targets; the search is the only thing that has produced steps.

## Operational gotchas

- Machine rebooted once (kills all nohup jobs: search, rating watch, schedulers). Check `ps` after any gap.
- Never `pkill -f <pattern>` / `pgrep -f` loops that can match your own shell (killed the session twice); use
  `ps -eo pid,args | grep "[p]attern"` and skip `$$`.
- Rating watch: `tools/watch_rating.sh <ids…>` (hangs occasionally on the API; restart if the log stops).
- Chrome with DevTools: `google-chrome --remote-debugging-port=9222 --user-data-dir=~/.local/share/kaggriculture-chrome`.
- typesafe.ai "Jev" key at `~/.config/typesafe/apikey` (never commit); SDK venv `~/.venvs/ts`; not usable in-game, weak offline.

## v23 first read (14:05 local, 27 games): rating 805, 16–11

Wins vs 614–806; losses vs 723–892. Six of the eleven losses are within 4k (coin-flips). Our average score in real games is
~78k, well below the 94k of the pool tests: live opponents crash the shared markets harder than replays. In the five
lowest games our day-6 farm was identical (fixed opening) and the divergence is: (a) opponent floods milk/strawberry →
prices 1–13 by day 20 (both sides ~40–50k); (b) in the two clear losses our herd stayed at 3–4 cows (milk demand 1–2
shops, correctly not built) while **strawberry cells crowded out wheat although 5–6 wheat buyers were open** (we had 8–13
wheat tiles vs their 26–27) and the opponent ran 9 sheep into 3 yarn stores. The plan's crop order is fixed
(MELON, STRAWBERRY, WHEAT, …) regardless of relative value. A value-ordered allocation (yield/day × price, haircut by total
supply incl. the opponent's vs the town drain) was added as knob `crop_value=1`; its pool test was launched at handoff
(result in `scratchpad/crop_value_test.log`). If it beats gen-53 on both pools, build it as v24 (4 slots left today).

**Result:** `crop_value=1` LOST on both pools (ladder 19/34 +5.8k, top 7/25 −11.4k vs gen-53's 29/34 / 9/25). Same lesson as
every other hand rule: value ordering with quoted prices over-reacts (prices already reflect gluts; the fixed order's
strawberry bias is what the search tuned around). Leave it as a search knob only.

## Method correction (14:30 local) — do not undo

The repeated error was evaluating structural ideas as one-off swaps on a genome tuned for the old structure (they all
lose that way) and then hand-testing more of them while competing with the search for CPU. Rule from here: **every idea
goes in as a knob/switch and is judged only by the search with the other knobs re-tuned around it; promotion decisions use
the full pools, never a sample.** `evolve_market.py` now: 12 opponents/generation, structural switches (`herd_npv`,
`crop_value`, `geese_min`) flipped in a third of children, and the elite re-validated on the FULL pools every 8 generations
(`experiments/evolve_market_fullpool_<gen>.json`). Search restarted as `evolve_market.py 9` (log `evolve_market9.log`).
Use my time for things the search cannot do: new capabilities/knobs, opponent pools, bug-finding in the executor.

## Next steps (in order)

1. Read v23's next games (ListEpisodes) — where it loses, to whom, our score in losses.
2. Keep the mixed-pool search running; verify any elite with the standard recipe before spending a slot.
3. The remaining known gap is consistency vs the 3000-tier: herd-size variance and unused wheat/carrot/tomato demand.
   Try making those *search-tunable behaviours* rather than hand rules (e.g. knobs for late-herd growth conditional on milk
   shops, strawberry wind-down day, tomato/carrot activation thresholds) and let the mixed-pool fitness decide.
4. Add 1500–2500-rated opponents to the pool (need their submission ids from the leaderboard UI) so the fitness covers the
   tier between the ladder pool and the top pool.

## Session 2026-09-22 14:15–15:15 local (this section supersedes "Next steps" above)

**Ladder:** v23 (56446174) 18-13, rating ~794 after 31 games (losses to 720–890-rated opponents scoring 75–100k; our live
mean 78k). v22 705. 4 submissions left in the UTC day; none spent.

**Executor bugs found in the engine source** (`.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`,
engine 1.32.7 = current): one-shot crops decay 1 unit / 2 hours from hour 0 of the day after their max-yield day (carrot age 4,
wheat 5, melon 13) and grow only on watered days inside a window (carrot ages 2–3 → max 3 units unfertilized, wheat 2–4 → 4);
our carrot rule waited for 4 units / age 4, so in the two v23 losses analysed 22 of 35 sprint carrots rotted and the rest sold at
2 units, and wheat came off at 3 not 4 (harvested before its last watering). Shed holds 100 units; the night drop discards the
overflow (43–61 units/game). Fixed as default-on knobs in market.py: `harvest_decay`, `harvest_late_hour`, `shed_guard`,
`water_growth_mult` (the engine refuses HARVEST before first_yield_day — the rule checks RIPE). Verified: no failed harvests,
glut seed 104k→113k, seed 101 139k→143k vs pass. **Pools (eval/pool_eval.py):** fix 27/36 +8.6k | mid 1/30 −34.8k | top 10/25
−6.8k vs old executor 29/36 +9.7k | 1/30 −34.2k | 9/25 −3.8k; fair 5/8 +1.6k. Not a promotion by itself → left to the search.

**Search:** `evolve_market.py` fixed (5-char labels collided, every trace bucketed as ladder, empty top bucket would crash gen 7);
full-pool validation now buckets ladder/mid/top/pub and writes `evolve_market_fullpool_<run>_<gen>.json`; elites seeded from
v23/v22/best.json. New knobs: herd_until2/herd_rich_drain, tomato_until, carrot_mult, tomato_mult, egg_drain_min,
land_day1/2/3, land_n, liquidate_from + the fixes above (74 knobs). Pool: + `replays/mid/` (32 opponents 1500–2500, built by
`tools/build_pool.py mid <candidates.json>` from the leaderboard API capture with teamId+submissionId for all teams,
`scratchpad/leaderboard_resp.network-response` of session aec4845d; ListEpisodes rate-limits → 8 s spacing). Running:
`evolve_market.py 11` (log scratchpad `evolve_market11.log`, session 6bd47f41). Fitness = pass + 12 traces + 2 public bots.

**Discussion/Code tab (first look):** public Apache-2.0 agent `thomastschinkel/the-2945-farm-96-vs-the-top-10-public-bots`
= the byte-exact main.py that scored **2944.7 live** (sub 56269928): route-tape replayer + reflex layers (sale racing on the
public rival-sales signal, 451k-event sale library, shed guards, per-tile carrot-vs-wheat simulation, herd model). Other public
notebooks score 2200–2750. Its author's from-scratch demand-driven planner reached 990–1578 live (like ours); the open problem vs
the top 10 is the second half (≈10 tomato tiles from day 12, labour plan). Copies + README in `refagents/public/`; both are
reactive opponents in the search (`pub:farm2945`, `pub:shopwork`). Bench: v23 0-8 vs farm2945 (−40k/game), 0-8 vs shopwork.
Kaggle daily top-episodes datasets: `kaggle/kaggriculture-episodes-index` (manifest.csv → ~640 replays/day, median rating
~3040). Final ranking = single Bradley-Terry tournament after two post-deadline weeks. Mechanics confirmed from source: price =
f(market inventory) only, shops drain 1 unit/product every 4 steps, lockstep quotes (sell order position matters, timing vs the
opponent does not).

**Decision needed from the user:** 2800+ by 09-30 from the 794 line is not plausible (public author's identical attempt: ~1.5k).
Options: (a) build on the Apache-2.0 2945 chassis with attribution and add an edge (search-tune its reflex thresholds; its
unsolved second-half/tomato labour problem is where our auction executor could contribute); (b) keep the own line and use the
public bots only as sparring. Nothing committed; no submission spent today.
Public farm2945 vs our trace pools (native seeds, real env): mid 20/30 (+4.2k, ours 92k) | top 15/25 (+20.4k, ours 112k);
v23 old executor on the same pools: mid 1/30 (−34.2k) | top 9/25 (−3.8k). (Frozen traces flatter the racer: it sells before
recorded sales that cannot react.)

## 15:30 local — direction set: build on the public chassis

- **v24 = `submissions/v24_farm2945_base.py`** (byte-exact public farm2945 v9/4, Apache-2.0, attribution in file) submitted
  03:11 UTC as **sub 56451295** as the rating anchor / control; 3 slots left today. Rating watch: scratchpad `watch_v24.log`.
- **Reactive opponent pool** `refagents/public/` (README lists sources): farm2945 (2945), tetsutani demand-preserving (2750),
  alperen first-in-line (= V48 byte-identical, 2746), alperen market-rhythm, Ahmed V47 (2686) / V48 (2670) / V56 (newest),
  tetsutani shopwork (2248). Load with Kaggle's last-callable rule (V47 = `_y_agent_shopherd`, V48 = `_e335_agent`). Each
  game ~3–4 s.
- **Chassis tuner `experiments/evolve_chassis.py <seed>`**: 49 knobs = the chassis's module constants (V9_RACE_*, V9_CARROT_*,
  V9_HERD_*, _CA_*, _OR2_*, _HD2_*, _CS_*, _CH_*, _SR_*, opening BUY/SELL), applied by setattr on a fresh import (verified: the
  base genome ties the mirror exactly; RACE/CARROT overrides change play). Fitness = fair-env margin vs mirror (3 seeds) + 4 other
  public bots; FULL-CHECK every 6 gens = all 8 opponents × 8 seeds → `evolve_chassis_full_<run>_<gen>.json`. Running as run 1
  (log scratchpad `evolve_chassis1.log`). Log `experiments/evolve_chassis_log.jsonl`, best `evolve_chassis_best.json`.
- Promotion rule for v25+: candidate must beat the unmodified chassis head-to-head on the FULL-CHECK (mirror margin > 0 on ≥ 6/8
  seeds and no other opponent worse than base) — then build `submissions/v25_*.py` = chassis file + a short appended block that
  sets the tuned constants (keeps the file byte-exact above the block, attribution intact).
- Own-line search (`evolve_market.py 11`) stopped at gen 0 to free CPU; its state is in evolve_market_best.json / log.
- Next after tuning: the chassis author's unsolved second half (≈10 tomato tiles from day 12, labour plan) — try as an
  appended layer with our labour auction filling idle worker-hours; judge on the same FULL-CHECK plus the top/mid trace pools.

## 16:10 local — frontier moved; v25 submitted
- **v25 = `submissions/v25_chassis_g5.py`** (farm2945 + tuned constants block; gen-5 elite 46-18 vs public pool, base 36-21;
  block verified identical to make_agent on 2 seeds) submitted 03:58 UTC as **sub 56452284**. 2 slots left today. Active: v24+v25.
  v24 rating 1321 after 10 games (15:52).
- **The public frontier has moved past farm2945**: tetsutani demand-preserving (2750 public score) and Ahmed V56 both beat the
  unmodified chassis **8-0** (they carry the same v9/4 stack plus anti-clone layers: EXP283 clone-gated sale pre-emption, v44y
  clone-mode race horizon + lockstep best-response ordering, V219SKIP). v56 vs demand 6-2 (−168 mean: equal). Vs the 25 top
  traces: demand 24/25 +36.7k, v56 24/25 +36.7k, farm2945 15/25 +20.4k. → base for v26+ = v56 or demand (whichever is
  deterministic in mirror play; test in progress). `evolve_chassis.py` now takes `CHASSIS=farm2945|demand|v56` (auto-derived
  65 knobs from top-level constants for the latter two; files/logs tagged `_v56` / `_demand`). `tools/build_chassis_sub.py`
  builds the submission for any chassis. `eval/chassis_check.py base <genome.json>` = the promotion check.

## 17:00 local — measured negatives on the frontier chassis, v26 submitted
- Constants tuner on demand-preserving (65 auto knobs, 11 gens): gen-11 elite vs base within noise on every opponent
  (mirror +213, v56 +45 vs −168, others ±100). The file is at its optimum for its constants → tuner stopped.
- Clone-detection hypothesis: a rival with its 3 clone gates disabled ties 7/8 mirror games (+16). The clone layers do not
  decide mirror games. The hand-permutation layer (`layers/depermute_block.py`) collapses the tape (9.6k) — negative, kept for record.
- **v26 = `submissions/v26_demand_base.py`** (byte-exact tetsutani demand-preserving) submitted ~04:55 UTC; active = v25 + v26
  (v24 retired from play at 1761 after 24 games, 23-1). 1 slot left today. Pending tests: opening quantities sweep
  (`scratchpad/opening_sweep.log`), `_ALT_MODE` EarlyCycle vs HybridOpening (`altmode_test.log`); modes available:
  Original / EarlyCycle / HybridOpening / Mixed (Dmitrii Gluzdov block at the end of the demand file).
- Opening-quantity sweep on demand-preserving (8 seeds vs mirror/v56/farm2945): 20/15 is optimal; 20/14 and 21/15 lose −250 to
  the mirror, 19/15 −7k, 16/12 −7.4k, 25/15 −1.8k, no opening −108k. `_ALT_MODE` EarlyCycle = identical results to HybridOpening.
  Conclusion: the frontier files are at a symmetric optimum vs relatives; constants, openings and clone gates are exhausted.
  Remaining lever = how the live top-10 beat this lineage (study running: `scratchpad/top_vs_lineage.log`).

## 17:20 local — what the 2800–2960 band actually is
Sampled 24 recent top-10 games vs 2780–2960 opponents (`scratchpad/top_vs_lineage/summary.json`, `top10_episodes.json`):
**none of the 24 opponents runs the public route-tape opening** (they open BUY WHEAT 13 / BUY 5 + COW 1 / HIRE×4 + 2 cows 3 sheep…).
The band's farms mirror the top-10 structure: 3 quadrants by day 10, 7–8 cows + 6–7 sheep + 3 geese, strawberries 23→29
tiles by day 14 then wound down from day 20, **tomatoes ~10 tiles days 14–20**, wheat 23–31 late, carrots late. Top-10 beat the
band 17-7 by +5k mean (105k vs 100k). The public chassis line (33 strawberries to day 24, 1 tomato, 16 wheat) is a different
species. New trace pool `replays/band2900/` (up to 40 distinct band opponents from those games, built by `scratchpad/build_band.py`);
`scratchpad/band_eval.py <who…>` scores demand/v56/farm2945 against it (`band_eval.log`).
- Public chassis vs the band2900 pool (40 frozen traces of 2780–2960 opponents, native seeds): demand 33-7 +18.8k, v56 33-7
  +18.6k, farm2945 31-9 +17.8k (ours ~107k vs 88k). Frozen traces flatter a sale-racer, but the lineage sits comfortably above
  the band → the 2800+ target rests on this base; live confirmation from v25/v26 over the next day. v25 1850 after 15 games.

## 2026-09-23 14:00 local — overnight ladder
| sub | agent | games | record | rating path → now |
|---|---|---|---|---|
| v26 56453495 | demand-preserving byte-exact | 153 | 82-71 | 681→1927→2318→2442→2457 peak→**~2400–2445** (bronze line ≈ 2450) |
| v25 56452284 | farm2945 + tuned constants | 156 | 87-69 | →2186 peak→**~2110–2160** |
| v24 56451295 | farm2945 byte-exact (retired) | 24 | 23-1 | 1767 |
Losses are coin-flips vs peers: v26 scores 97.6k vs 99.0k in its 66 losses (opponents rated 2222–2576). The demand lineage rates
~280 above farm2945+tuned in the same field. Public scores quoted in the notebooks (2750/2945) were earned in an older field.
Next: profile v26's live losses (`scratchpad/live26_profile.py` → `live26_profile.log`, pool `replays/live26/`), v27 = V56
byte-exact submitted 14:05 local for the lineage comparison (retires v25). 4 slots left today.
- **Live classification of v26's 134 games vs ≥2200 opponents** (`scratchpad/live26_classify.py`, `live26_classified.json`,
  replays in `replays/live26/`): 127 are clones of this chassis (82 with exactly our step-0 signature BUY 20 / SELL 15 / BUY_SEED
  WHEAT 1 = demand/v56 lineage; 18 farm2945's BUY 20 / SELL 15; 10 V47/V48's BUY 7 / SELL 2). Record vs clones: <2400 31-18 (63%),
  2400–2500 27-41 (40%), 2500+ 2-8. Vs the 7 non-clone adaptive farms 3-4. The 2400 band is a swamp of the same public files;
  copies rated 2500+ beat us, so stronger variants (v56? private tweaks) exist above. In losses the rival sells more milk/strawberry/
  wool/wheat and we dump more fertilizer → lost sale races. v27 = v56 byte-exact live since 14:05 (sub 56479438).
- **64-seed head-to-head on the demand chassis** (`eval/chassis_check.py`, seeds 601–664, `scratchpad/chassis_check_demand_64.log`):
  base vs itself 4-2 (58 ties), vs v56 8-56 (+14); **gen-11 elite** (`experiments/v28_demand_genome.json`) vs unmodified file
  45-19 +500, vs v56 26-38 +271, all other relatives ≥ base (ALL 450-62 vs 387-67). Promoted as **v28 = sub 56481283** (15:35 local; `submissions/v28_demand_g11.py`
  = demand file + constants block via `tools/build_chassis_sub.py`). Tuner run 2 (CHASSIS=demand FRONT_SEEDS=4, log
  `evolve_chassis_demand2.log`) continues; any later elite must pass the same 64-seed check before it replaces v28.

## 2026-09-23 16:30 — two corrections and a negative
- **BUG (evaluation): `fair_env.apply()` was process-wide with no restore.** In every ProcessPoolExecutor that mixed fair-env
  games (pass / agent-vs-agent) with replayed traces, workers kept the patched weed pass for later trace games → shop draws
  differed from the recorded game → the trace opponent was unfaithful. Contaminated: `evolve_market.py` fitness and
  `eval/pool_eval.py` trace buckets (pass job runs first in each worker), `frontier_cmp` ("demand 24/25 vs top" is WRONG),
  the own-line pool numbers in general. Clean: `band_eval`, `pub_vs_pools`, `chassis_vs_top`, `hybrid_eval` traces (fair jobs
  last), all `evolve_chassis` / `chassis_check` numbers (fair only). Fixed: `fair_env.restore()` + `is_applied()`; trace
  branches now call restore(). Clean re-measurement vs the 25 top traces is in this section below.
- **Hybrid (tape days 0–11, our market planner from day 12 or 16) = NEGATIVE**: band2900 9-31 (−15.8k), top 8-17, live clones
  0-20 (−37k), vs demand/v56 0-8 (−39k); the pure chassis on the same games: 33-7 / 15-10 / 3-15 / 1-0 / 2-6. Our planner loses
  ~30k over the second half relative to the tape. `kaggriculture/agents/hybrid.py` kept; do not resubmit this idea without a
  much stronger second-half executor.
- Clean re-measurement vs the 25 top traces (shipped env, `scratchpad/top_clean.py`): demand 15-10 +20.1k, v56 15-10 +20.5k,
  farm2945 15-10 +20.4k. The three public files are equal against the top tier; the "24/25" earlier in this file is void.

## 2026-09-23 20:15 — executor rebuild, live picture, hybrid search
- **Live**: v28 (demand + tuned) 2245 after 81 games, v27 (V56) 2011 after 80, v26 (retired) 2378. All sub-2200 losses of v27/v28
  are coin flips (−16…−2,000) vs COPIES of the same file (identical day-12 farms) → the copy swamp now spans 1800–2550.
  Trace gate (`scratchpad/trace_gate.log`, 122 diverse traces): v28 genome 93-29 vs base 81-39 (live26 clones 32-18 vs 20-28).
- **Tour executor** (`kaggriculture/agents/tour.py`, `executor="tour"` knob): fixed daily zone tours + need-based supplies. From
  the tape's day-11 farm vs pass: tape 137k, auction hybrid 103k→106–113k after the wheat-carrier fixes (`feed_per_carrier`,
  `pickup_value`: one carrier used to take the whole shed's wheat), tour hybrid 99k. Neither executor is the bottleneck; the
  second-half deficit (~25k) is planner/market rules: animals unfed on some days → escapes (26→20), strawberries under-fertilized
  (2–5 applications/day vs ~16 windows; `fert_reserve_mult` did not help), wheat tiles lapse, smaller carrot sprint.
- **`experiments/evolve_hybrid.py`** (running, run 1, log `evolve_hybrid1.log`): search over the ~50 second-half knobs of the
  hybrid (tape days 0–11 → our planner/executor), fitness = coins vs pass from the tape's day-11 farm on 3 seeds + margin vs the
  tape (fair env). Target: ≥137k vs pass (the tape's own number). Tuner run 4 (`evolve_chassis_demand4.log`, trace-augmented
  fitness) continues at 8 procs.
- fair_env leak fixed (`restore()`); all trace evaluations since 16:30 are clean.
- 21:50 hybrid search gen 53: vs pass 141k (tape 161k) on the 3 seeds, margin vs tape −14.7k (from −47k at gen 0). Full pools for
  the gen-49 elite (`scratchpad/hybrid_eval_best.log`): band 9-31 −12k, top 8-17 −5k, live26 0-20 −31k, demand/v56 0-8 −27k (tape
  on the same games: 33-7 / 15-10 / 3-15 / 1-0 / 2-6). Improving but far from parity; left running overnight (run 1, JOBS=12),
  auto full-eval when tape-margin > 0 or gen 150. Tuner run 4 continues. v28 2238 @89, v27 2022 @84. 3 slots left today unused.

## 2026-09-24 01:00 — hybrid search: dead end; tuner run 4 elite under the gate
- Hybrid search plateaued: gen 53 → gen 152 moved the tape margin only −14.7k → −13.1k; full pools unchanged (band 9-31 −12.7k,
  live26 0-20 −33k, demand/v56 0-8 −28.6k vs the tape's 33-7 / 3-15 / 1-0 / 2-6). Our planner's second half caps ~25–30k below the
  tape against relatives whatever the executor. **Stopped.** The takeover idea needs the winners' second-half targets
  (shop-conditioned table from the daily top-episodes dataset), not more knob search.
- Tuner run 4 (trace-augmented fitness) gen-17 elite full check: mirror +768, v56 +611, all relatives ≥ base, traces 104/122
  +8.5k. 64-seed gate vs base and vs the v28 genome running (`scratchpad/chassis_check_run4.log`).
- v28 2227 @96 games (24-28 vs 2200–2400; v26 was 34-22 there two days ago), v27 2004 @97 (V56 lineage weaker live; dropped).
  **v29 = sub 56493719** = byte-exact demand file again (identical to v26), submitted 01:05 local as a same-field control: over the next
  hours v28 (tuned) vs v29 (base) climb through the same population → decides whether the tuned constants help live. 2 slots left today.
- **64-seed gate** (`scratchpad/chassis_check_run4.log`): run-4 gen-17 elite ALL 498-14 +5.2k: mirror 59-5 +1,334, v56 57-7
  +1,161, every other relative >= base; traces 104/122 +8.5k (base 81/122). v28 genome for comparison: mirror 45-19, v56 26-38.
  -> **v30 = sub 56495224** (`submissions/v30_demand_g4_17.py`, genome `experiments/v30_demand_genome.json`, 52 constants) submitted
  01:25 local. Active: v29 (base, sub 56493719) + v30 (tuned) in the same field -> the live A/B. 1 slot left today. Tuner run 4 continues.

## 2026-09-24 07:00 — same-field A/B decided: tuned constants help live
| | games | rating | vs <2200 | vs 2200-2400 |
|---|---|---|---|---|
| v30 tuned (sub 56495224) | 81 | **2244** (2194@60, 2249@80, climbing) | 54-11 | 10-6 |
| v29 unmodified file (sub 56493719, = v26) | 79 | 2113 | 42-25 | 2-9 |
The base file that reached 2378 two days ago plateaus ~2110 today: the copy swamp now reaches 1800, so ratings are only comparable
within the same field/time. The offline 64-seed gate predicted v30 > base (59-5) and the ladder confirms it (+130 in the same field).
**Direction:** the constants search is the only lever that has moved the ladder; it gets the CPU. Next: tuner with v30's constants as an
extra reactive opponent (arms race vs our own best), same 64-seed gate (+ trace term) before any slot. Final picks by 09-30: the two
strongest by gate + live plateau (currently v30, then v28/v26). Hybrid/tour/second-half work parked (see 01:00 entry).

## 2026-09-24 09:15 — two more measured negatives on the 3000 question
- **Rank-1 farms as tapes**: DSM's 28 recorded games replayed open-loop vs the reactive chassis on native seeds: 1-27; replayed
  value 59k vs 116k recorded (`scratchpad/dsm_tape_test.py`). Adaptive farms cannot be taped; the route-library path is closed.
- **Tomato swap of the tape's day-11 strawberry batch** (`layers/tomato_swap_block.py`, K=13): vs mirror 1-7 −7.9k, v56 1-7 −8.1k,
  self(v30) 1-7 −8.6k, pass −17k mean (seed 601: −2.6k). Tomatoes worked (4 units/tile, 50 sold at $50–63) but the tape digs the
  finished tiles on day 23 and never replants (13 idle tiles for 6 days) and its strawberry sale plan loses its lots. Negative.
- Conclusion stands: no measured path to 3000 within the deadline; the tuned-chassis line (v30 lineage) is the final vehicle.

## 2026-09-24 09:40 — v31 (run-5 elite) submitted; arms race continues
- Gate (`scratchpad/chassis_check_run5.log`, 64 seeds): run-5 gen-11 elite vs v30's constants **57-6 +629**, mirror 61-3 +1,510
  (v30: 59-5 +1,334), v56 57-7 +1,314 (v30: +1,161), other relatives equal, traces 105/122. -> **v31 = sub 56508691**
  (`submissions/v31_demand_g5_11.py`, genome `experiments/v31_demand_genome.json`, 54 constants). Active: v30 + v31 (same-field
  A/B of two tuned generations); v29 base control retired at ~2100. Live at submit: v30 2256 @90. No slots left in this UTC day.
- Tuner run 6 started with SELF_GENOME = v31 (log `evolve_chassis_demand6.log`); gate for its elites = chassis_check vs v31 on 64 seeds
  (auto-armed). Lesson for this file: never write HANDOFF via an unquoted heredoc (backticks execute).
- 16:40: run-6 gen-11 elite vs v31: 30-34 +318 (mirror 60-4, v56 58-6) → does NOT clear the gate; constants line converging around
  v31. Live: v31 2408 @45 (v30 was 2145 @40), v30 2328 @127. 5 slots available (new UTC day since 12:00 local); none spent.

## 2026-09-24 17:35 — same-field A/B across three generations (rating at game 60)
| | @20 | @40 | @60 | now | vs <2200 | vs 2200-2400 | vs 2400-2500 | vs 2500+ |
|---|---|---|---|---|---|---|---|---|
| v31 run-5 constants (sub 56508691) | 2290 | 2402 | **2498** | 2495 @63 | 19-0 | 9-5 | 16-9 | 3-2 |
| v30 run-4 constants (sub 56495224) | 1868 | 2145 | 2194 | 2322 @131 | 57-12 | 41-21 | | |
| v29 unmodified file (sub 56493719) | 2303 | 2105 | 2088 | 2109 @116 | 56-42 | 4-11 | 0-1 | |
The offline 64-seed gate has predicted the live order every time (base < v30 < v31). v31 is above the bronze line (~2450) and
still climbing. Final-pick order today: v31, v30. Tuner run 6 (target v31) continues; its gen-11 elite failed the gate (30-34).

## 2026-09-24 18:10 — v32 (run-6 gen-29 elite) submitted
- Gate (`scratchpad/chassis_check_run6b.log`, 64 seeds): vs v31's constants **39-25 +440**, mirror 64-0 +1,687 (v31: 61-3 +1,510),
  v56 59-5 +1,385 (v31: 57-7 +1,314), all other relatives >= v31, traces 106/122. -> **v32 = sub 56515072**
  (`submissions/v32_demand_g6_29.py`, genome `experiments/v32_demand_genome.json`). Active: v31 + v32 (same-field A/B); v30 retired
  at 2329 @134. v31 at submit: 2507 @71. 4 slots left in this UTC day. Tuner run 7 started with SELF_GENOME = v32
  (`evolve_chassis_demand7.log`); gates auto-armed vs v32.
