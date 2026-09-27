# Kaggriculture — session handoff (2026-09-27, 15:15 NZDT / 02:15 UTC)

Read this first; `HANDOFF_LOG.md` is the full chronological log (2026-09-22 → 09-25) with every measurement.
Competition: https://www.kaggle.com/competitions/kaggriculture (2-player farming sim, 720 turns, most coins wins).
**Deadline 2026-09-30 23:59 UTC.** 5 submissions per UTC day (local = UTC+12, quota resets 12:00 local).
Account IWA_setu (user `sdcarson`), token `~/.kaggle/access_token`. Repo `/home/iwa/working/kaggle`, branch `agent/livestock-v6`,
PR #2 → main: https://github.com/warlord-2227/kaggle/pull/2 (last commit `4442889`, pushed). Engine `kaggle-environments` 1.32.7 (current).

## 1. The rules that decide everything (verified on the Overview → Evaluation page and by Kaggle staff in the forum)

- **Only the latest 2 submissions are tracked, and they are the final pair.** There is no manual selection. Each new submission
  retires the older of the two active ones. Submit the agent you want to keep LAST.
- At the deadline submissions lock; games continue ~2 weeks; a **Bradley-Terry fit on WIN/LOSS** over all episodes ever played
  between submissions still active decides the final leaderboard. Margin is irrelevant; at 2250+ the median gap is $177 and 78%
  of games are decided by < $1,000 → optimise paired win rate. Post-deadline games dominate the evidence, so a late submission is
  fine; a retired submission's history is lost.
- Live rating: new submissions start at 600, need 40–70 games to settle, overshoot early; only the band where you win ~50% is
  your level. Ratings are comparable only for submissions climbing through the same field at the same time.

## 2. Where we stand

| sub | file | what | live now | note |
|---|---|---|---|---|
| **v35** 56595044 | `submissions/v35_cha22_g4_59.py` | **cha22 base + run-4 gen-59 constants** (genome `experiments/v35_cha22_genome.json`) | submitted 09-27 15:11 NZDT (02:11 UTC) | **active** |
| **v34** 56559582 | `submissions/v34_cha22_g4_17.py` | cha22 base + run-4 gen-17 constants (genome `experiments/v34_cha22_genome.json`) | 1796 @ 121 (107-14, still in low matchmaking) | **active** |
| v33 56553451 | `submissions/v33_cha22_g3_17.py` | cha22 base + run-3 gen-17 constants | plateau 2308 @ 209 (65-41 vs 2200–2400, 3-5 vs 2400+) | retired by v35 |
| v32 56515072 | `submissions/v32_demand_g6_29.py` | demand-preserving + run-6 constants | 2367 @ 202 | retired by v34 |
| v31 56508691 | `submissions/v31_demand_g5_11.py` | demand-preserving + run-5 constants | 2411 @ ~200 (peak 2526; 28-40 vs 2500+) | retired by v33; re-submit it if v33 disappoints |
| v30 56495224 | `v30_demand_g4_17.py` | run-4 constants | 2337 (retired) | |
| v29 56493719 | `v29_demand_base_again.py` | unmodified demand file (same-field control) | 2109 (retired) | |
| v26 56453495 | `v26_demand_base.py` | unmodified demand file, 2 days earlier | 2378 (retired) | field was weaker then |
| v23 56446174 | our own market agent | 783 | | own line parked |

Same-field A/B at game 60: v31 2498 / v30 2194 / v29 (base) 2088 → the constants search moved the ladder +300–400 over the
unmodified file; v32 vs v31 was inside the noise (2383 vs 2498 @60). v31/v32 both settled at **~2400** (their 50% band). Bronze line
≈ 2450; 3000+ needs a different species (see §5). 4 submission slots left in the current UTC day (resets 13:00 NZDT). **Active pair = v34 + v35, both run-4 cha22 builds.**

## 3. The ladder, as measured

- 1800–2550 is a swamp of copies of the public route-tape chassis (127 of v26's 134 opponents ≥2200; 82 with our exact opening).
  Games between copies are decided by sale races and SELL-slot order (±$1k). Copies rated 2500+ beat v26 8-2.
- 2500–2960 = adaptive farms (diverse; ~10 tomato tiles d14–20, strawberries wound down from d20, 25–30 wheat late). The
  top-10 beat that band 17-7 by +5k. Frozen replays of them lose to the chassis 33-7; live they win → their edge is reaction.
- **The public frontier moves every few days.** Code tab by score at 23:15 on 09-25: V38 2625, V39 2621, v34 2602, V53 2598, V55 2596,
  V41 2586, master-engine-v53e 2581, Kaggricult-Man 2579, public v31 2576, V43 2551, …, Master Engine V3 2516 (re-run 09-25, now
  packed as SOURCE_BYTES, **byte-identical to cha22**), Herd Safe v3 2513; cha22/Multi-Route fell out of the top 20 (notebook scores
  are live ratings and drift). `cha22.py` (entry `ig_agent`, 7,482 lines, V39 + v9 layers + EXP239–241 learned route choice) beats
  the demand file 8-0 +3.2k, V56 8-0, farm2945 8-0, our v31 7-5 −1.0k (12 seeds) but only **30-34 +540 over 64 seeds**.
- **09-25 23:27: every unmeasured top file pulled and measured vs cha22** (12 paired seeds, `analysis/scripts/newpub_vs_cha22.py`;
  files now in `refagents/public/`, README has sources): v34 12-0 +9.2k, V41 12-0 +6.5k, master-engine-v53e 12-0 +6.5k, V43 12-0
  +5.7k, Herd Safe v3 10-2 +2.3k, Kaggricult-Man (`marketshock_m1_leoprovorov.py`, agent from its dataset) 11-1 +3.2k via
  `module.agent` (its *last callable* is a patch factory that plays nothing → 3,000 coins). All are the same V39 lineage (89–92%
  shared lines). **cha22 stays the base.** Herd Safe v3 and marketshock are the closest relatives → extra gate opponents if wanted.

## 3b. Gap analysis (09-26 19:00–21:30): where the 10–20k/game to the top comes from — SELLING, not farming

Scripts `analysis/scripts/{income_gap,cash_ledger,demand_vs_supply,sale_quality}.py` over live replays: rank-1's games (`replays/top`,
25 sides), top-10 vs 2900-band (`replays/band2900`, 40), v33's live games (`replays/live_56553451`, 39). Ledger balances to <200 coins.
- Gross sales are equal (v33 140.8k, rank-1 142.6k, top-10 134k) and v33's costs are LOWER (23k vs 27–32k). Final coins: v33 93.6k,
  top-10 104.4k, rank-1 114.2k. The gap is net product income: wool −7k, tomato −5.6k (v33 has 2 tomato tiles vs 12–14), egg −1.2k
  vs top-10; vs rank-1 also strawberry −4.4k, milk −3.5k.
- Engine facts (`kaggriculture.py`): demand is tiny and fixed — each unlocked shop takes 1 unit of each product it lists every 4 steps
  (2 if single-product: YARN_STORE, PET_CAFE), town centre 1/product/day; nothing else buys. Price = f(inventory − 10,000): wool sq
  (105 excess units → floor 1), melon sq, milk/strawberry linear (~2 coins per excess unit), wheat/egg log (flat). Seeds/animals are
  fixed price; hires cost fib(n-th hire of the day).
- Realised price per FILLED unit (shed deltas, pure-sell steps): wool v33 92 vs rank-1 136 / top-10 170; strawberry 53 vs 148 / 123;
  milk 58 vs 103 / 144. v33 sells at inventory +30…+45 above baseline (quoted 50–58), rank-1 at/below baseline. Rank-1 drips 1.7
  wool units per order and sells its whole stock 16% of the time; v33 dumps the whole stock 72% of the time. Eggs/wheat/carrots fine.
  Yarn store absent in ~half the towns → wool demand 1/day → any wool beyond that is worth ~0 (rank-1 sells 56 wool units in those
  towns vs 193 when present; v33 124).
- **Sale-metering tested and REJECTED (09-26 18:50, `experiments/sell_gate_ab.py`, 16 seeds × both seats):** holding SELL of
  wool/strawberry/milk/melon while quoted < 0.8·base (unless shed ≥ 70 or day ≥ 28) → 0-32 vs every opponent, **−10.1k own coins
  paired**, and the opponent GAINS ~+24k (seed-601 diagnostic: demand file 82.5k → 106.4k). The market is shared: whatever we hold,
  the opponent sells into the better price. In a copy-vs-copy game selling is a race (the handoff's 'sale races'), and the chassis
  already races. The top agents' higher unit prices come from producing LESS of the glutted products (sheep only with a yarn store,
  ~10 tomato tiles, strawberries wound down after d20) — a production-plan change, not a selling rule. On this tape that means a
  replant executor (finished tiles → tomatoes/wheat) and shop-aware herd sizing; the tomato swap (−8k) and our own executor (25–30k
  behind the tape) are the measured history of that road. Not attempted with 4 days left.
- **Wool split by town (09-27, `analysis/scripts/wool_gap.py`):** with a yarn store v33 is 17k behind the top-10 (11k wool) with the
  same sheep count, care and harvests — it is the shared-market race (realised 112/unit vs 210). Without a yarn store v33 keeps 5.6
  sheep all game (top-10 3.6 → 1.6 by d28) and sells wool at 2/unit. **Sheep-cut tested and REJECTED** (`experiments/sheep_cut_ab.py`:
  from day 12 in no-yarn towns stop FEED/CARE on sheep so they escape, drop sheep buys): paired −1.4k/game vs demand/v31/v56,
  wins 4-10; **−1.0 to −1.4k even on no-yarn seeds** (sheep also yield daily fertilizer, the tape buys the feed wheat anyway, and
  the yarn store unlocks ~day 11–12 so an early cut kills sheep in towns that get one). Engine: an animal unfed 2 days escapes;
  care+fed = +1 unit on the next production day. CAVEAT: that 224-game run overlapped a swap thrash (28/29 GB) and the engine has a
  1 s act timeout; a clean re-run after the tuners were killed (day-15 cut, 8 seeds × both seats vs demand) gave paired **+97 overall,
  +388 on the 4 no-yarn games but 2 wins flipped to losses**, yarn games identical (no cuts). Net: ≈ +200/game, win-rate neutral or
  worse → not worth a slot. Lesson: the tape's fixed plan cannot be trimmed piecemeal; only a different plan (tomatoes where a
  pizza shop / farmers' market exists: +6k gap in 36/39 towns; geese for egg shops) moves the needle, and that is executor work.

## 4. Current work: constants search on the cha22 base → v33

- Tuner: `experiments/evolve_chassis.py` (`CHASSIS=cha22`, 77 auto-derived knobs = the file's top-level numeric/bool constants,
  applied by setattr on a fresh import; `make_agent` returns the LAST callable — bug fixed 09-25 18:05, all earlier cha22 numbers
  void). Fitness = paired WIN RATE (margin tiebreak, clipped ±10k) vs mirror ×3 seeds + demand/v56/**v31** ×3 seeds + 2 rotating
  relatives + 4 diverse frozen traces (`replays/{mid,band2900,live26}`, shipped env via `fair_env.restore()`).
- **Tuner runs 3 and 4 STOPPED 09-27 19:16 NZDT** (machine at 28/29 GB swap after two days; the search had been flat since
  gen 5; last elites: run 3 gen ~205, run 4 gen ~80, all full-checks saved under `experiments/`). Do not restart them.
- (History) Running from 09-25 ~18:05: run 3 (`JOBS=16`, log
  `/tmp/claude-1000/-home-iwa-working-kaggle/6bd47f41-8734-4dbd-ac5b-417bd3dc752e/scratchpad/evolve_chassis_cha22_3.log`, gen 26 at
  23:30, ~10–14 min/gen) and run 4 (`JOBS=6`, `evolve_chassis_cha22_4.log` same dir, gen 9, ~26 min/gen). Elites:
  `experiments/evolve_chassis_cha22_best.json`, full checks every 6 gens `experiments/evolve_chassis_cha22_full_<run>_<gen>.json`
  (3_005, 3_011, 3_017, 3_023, 4_005 exist). Tuner full-checks are flat across gens (margin +3.7–3.9k, wins 0.87–0.94).
- **Gate results (64 seeds × 11 opponents; base cha22 = ALL 594-51 +4,084, v31 30-34 +540, v56 61-3, demand 61-3):**
  - gen-11 (`full_3_011`, `experiments/chassis_check_gate_3_011.json`): mirror 38-26 −18 (fails the 42-22 bar), v31 39-25 +737.
  - **gen-17 (`full_3_017`) → v33: mirror 57-7 +384, v31 41-23 +671, demand 64-0, v55 64-0, v56 63-1, ALL 667-37 +4,158** — every
    opponent held or better (`experiments/chassis_check_gate_3_017_023_4_005.json`).
  - gen-23 (`full_3_023`): mirror 41-23 +89, v31 31-33, v56 53-11 — worse than gen-17 everywhere (later gens drifted).
  - run-4 gen-5 (`full_4_005`): mirror 53-11 +162, v31 35-29 +552 — passes the mirror bar, weaker than gen-17.
  - run-4 gen-11 (`full_4_011`, gate armed by the previous session, done 09-26 03:20): mirror 52-11 +234, v31 39-25 +630, v55 64-0,
    all others held — passes the bar, still below gen-17.
  - **run-3 gen-35 (`full_3_035`, gate done 09-26 05:07, `experiments/chassis_check_gate_3_035_4_011.json`): mirror 60-4 +581,
    v31 41-23 +741, demand/firstline/rhythm/v47/v56/shopwork/v55 64-0, farm2945 62-2, v48 63-1, ALL 674-30 +4,256** — the best
    gate so far, ≥ gen-17 everywhere. Built as `submissions/v34_cha22_g3_35.py` (genome `experiments/v34_cha22_genome.json`), NOT
    submitted yet (verified 05:20: file == genome on seeds 601/602, entry `ig_agent`). **Direct h2h gen-35 vs v33 genome, 64 seeds ×
    both seats (`analysis/scripts/genome_h2h.py`): 93-33 (47-16 / 46-17), margin +176** — a seat-symmetric 74% edge. Plan: submit v34
    once v33 has ~60–70 live games and sits ≥ 2400 (it retires v32); if the cha22 lineage disappoints live, re-submit v31's file instead.
  - Later elites vs the **v34 genome** (h2h, 64 seeds × both seats, `h2h_053_4017_vs_v34.log`): run-3 gen-53 **50-76 −263** (run 3 has
    drifted past its best; gen 35 stays its pick); **run-4 gen-17 82-46 +147** (40-24 / 42-22) → gate vs base started 07:19
    (`gate_4017.log` → `experiments/chassis_check_gate_4_017.json`). Rule: it replaces v34 only if its base gate is ≥ gen-35's
    (mirror ≥ 60-4-ish, v31 ≥ 41-23, no opponent lost) — beating our own elite alone is the arms-race trap (§5).
  - **run-4 gen-17 gate (08:20, `experiments/chassis_check_gate_4_017.json`): mirror 60-4 +648, v31 39-25 +745, farm2945 64-0,
    demand 64-0, v55 64-0, ALL 669-35 +4,216** — equal to gen-35 on the base gate (674-30) and 82-46 over it head-to-head → chosen
    as **v34 = `submissions/v34_cha22_g4_17.py`** (genome `experiments/v34_cha22_genome.json` now points at 4_017; the gen-35 build
    is kept as `submissions/v34alt_cha22_g3_35.py`).
  - v33 live at 07:00: 66 games 62-4, rating 2106, opponents' median 1830, max 2101 — it has not yet been matched against 2200+; its
    climb is slower than v31's (2078 @60 vs 2498) purely because of the opponents drawn. Level still unknown.
  - 08:10 `analysis/scripts/live_classify.py 56553451 1900` (parametrised classifier; replays → `replays/live_56553451/`): all 39
    opponents ≥1900 are chassis copies (day-12 farm identical); v33 is 14-1 vs <2000 and **21-3 vs 2000–2200, mean margin ≈ +1.0k**
    — the swamp, decided by ±1k, and v33 is winning it. 72 games, 66-6, rating 2112 at 08:00 (game rate ~6/h now).
  - 09-27 10:00 local (NZDT now, UTC+13): **v33 plateau ~2340–2355** since game ~150 (183 games: 86-9 vs <2200, 56-28 vs 2200–2400
    with mean margin +125, 3-1 vs 2400+). Recent games are ±50–400-coin coin flips vs 2250–2400 copies (many brand-new 5657xxxx
    subs). Same level as v32 (2362) / v31 (2411) → the cha22 lineage is NOT a live upgrade over the demand lineage in the swamp,
    despite 41-23 offline vs v31. v34 107 games, 96-11, rating 1758 (still in low matchmaking). Decision: keep v33+v34 (not worse
    than v31+v32; v34 offline-strongest); nothing to resubmit unless v34 settles clearly below v33.
  - 09-27 12:40: v33 drifting down — 196 games, rating 2310, 3-4 vs 2400+, 59-35 vs 2200–2400. v34 112 games, 100-12, 1772 (slow
    matchmaking; needs ~1–2 more days to show its band). **Decision window: by 09-29 evening NZDT** (a re-submission needs ~1.5–2
    days to settle before the 10-01 12:59 NZDT lock). If v34 settles ≥ v33 and v33 < 2350 by then, consider re-submitting
    `submissions/v31_demand_g5_11.py` (retires v33 → pair v34 + v31-copy). Do NOT submit anything that retires v34 unless v34 is
    clearly the worst.
  - 09-27 13:05: Code tab unchanged since 09-25 (no new public base). Tuner still running (run 3 gen ~200, run 4 gen ~75).
    h2h vs the v34 genome (64 seeds × both seats): **run-3 gen-185 103-25 but margin −343** (wins tight races, loses a few big);
    run-4 gen-59 86-40 +107. Base gate on both started 13:05 (`gate_185_4059.log` → `experiments/chassis_check_gate_3_185_4_059.json`).
    If gen-185 holds every opponent (mirror ≥ 60-4, v31 ≥ 39-25, no big-loss opponent) it is the v35 candidate to replace the
    plateaued v33 (submitting retires v33, keeps v34).
  - **Gate 15:09 (`experiments/chassis_check_gate_3_185_4_059.json`):** gen-185 mirror 59-5, **v31 47-17 +66** but demand 59-5, v56
    58-6, v55 59-5, farm2945 60-4 (ALL 649-55) → arms-race trade, REJECTED. **run-4 gen-59: mirror 63-1 +780, v31 40-24 +770, farm2945
    64-0, demand 62-2, v56 62-2, v55 62-2, ALL 670-34 +4,286** — ≥ v34 everywhere within noise, 86-40 over v34 h2h → **v35 =
    `submissions/v35_cha22_g4_59.py`** (genome `experiments/v35_cha22_genome.json`), replaces the plateaued v33.
  - 12:10 local: v33 95 games, rating 2205 (80-7 vs <2200, **7-1 +430 vs 2200–2400**); v34 55 games, rating 1587, 52-3. Game rate
    2–6/h each, so v33 needs ~another day to show its 50% band. Decision pending: if both settle ≥ 2400 the pair stands; if the
    cha22 line settles < 2400, re-submit `submissions/v31_demand_g5_11.py` (order = the keeper last).
  - Build verified (`analysis/scripts/verify_build.py`, seeds 601/602 vs demand: file == make_agent(genome) rewards, entry `ig_agent`).
    Note: `tools/build_chassis_sub.py` reads the chassis in text mode, so the CRLF public file becomes LF in the submission; the
    prefix is identical after normalisation (checked) and Python semantics are unchanged.
  - Any later elite must beat **v33's** numbers (mirror ≥ 57-7 is unlikely to be exceeded; require v31 ≥ 41-23 and mirror ≥ 42-22 vs
    the raw base, plus ≥ 42-22 vs the v33 genome as SELF_GENOME if an arms-race check is wanted).
- **Gate before any submission**: `CHASSIS=cha22 .venv/bin/python eval/chassis_check.py base <elite.json> --seeds 601-664 --jobs 8`
  (64 seeds × 11 reactive opponents incl. v31/v55/cha22-mirror). Promote only if the elite beats the base head-to-head
  (≥ 42-22) and holds every other opponent's margin; the same 64-seed gate predicted the live order base < v30 < v31 correctly and
  correctly flagged v32 vs v31 as noise (39-25).
- Build/submit: `.venv/bin/python tools/build_chassis_sub.py cha22 <elite.json> submissions/v33_cha22_<tag>.py --tag "v33 ..."`
  (appends a constants block to the byte-exact public file, Apache-2.0 notices kept), verify with 2 seeds that the file and
  `make_agent(genome)` give identical rewards (see the v30–v32 build cells in HANDOFF_LOG), then
  `.venv/bin/kaggle competitions submit -c kaggriculture -f <file> -m "..."`. Submitting v33 retires v31 → pair v32 + v33; if v33 is
  clearly the best, consider re-submitting `submissions/v31_demand_g5_11.py` afterwards so the pair is v33 + v31-copy (order: the
  one to keep goes last).
- Live monitoring: `tools/collect_episodes.sh` (running, saves ListEpisodes JSON to `analysis/data/live/`); same-field A/B report
  `analysis/scripts/ab_report.py` (edit the ids at the bottom; queries the API directly), classifier `analysis/scripts/live26_classify.py`
  (clone vs adaptive by day-12 farm), `analysis/scripts/cha22_strength.py` / `newpub_test.py` / `newpub_vs_cha22.py` (new-file
  measurement). These were session-scratchpad files and are now committed. `tools/watch_rating.sh` is not running.

## 5. What was measured and rejected (do not redo; numbers in HANDOFF_LOG.md)

- Our own agents (`kaggriculture/agents/market.py` demand-driven planner + coin-priced labour auction, `tour.py` zone-tour
  executor, `hybrid.py` tape days 0–11 → our planner): ceiling ~800 live; from the tape's own day-11 farm vs a passive opponent
  the tape makes 137k, ours 106–113k with either executor; the hybrid knob search (`evolve_hybrid.py`, 150 gens) plateaued at
  −13k vs the tape. Executor bugs fixed on the way (carrot/wheat decay timing, shed overflow, wheat-carrier split) are in market.py.
- On the public chassis: opening quantities (20/15 optimal), `_ALT_MODE`, clone-gate blinding (7/8 ties), hand-permutation
  (collapses the tape), race-horizon jitter (+50–100, noise), SELL-slot shuffle (−2k → slot order matters, already optimised by
  ORDERPRI2/v44y), tomato swap of the day-11 strawberry batch (−8k: the tape digs finished tiles and never replants), rank-1's
  farms replayed as tapes (1-27; adaptive farms cannot be taped), wider search ranges (drift), arms race vs our own elite only
  (overfits; keep base/v56 margins in the gate).
- Forum-measured by others: selling earlier −80k, splitting sales −60k, holding stock −2.3k; RL reaches silver at best (rank 28,
  macro PPO + BC, 300k games); behaviour cloning at 99% agreement scores ~0.
- Evaluation pitfalls fixed: `fair_env.apply()` leaked into replayed traces in shared workers (now `restore()` in every trace
  branch); mean-margin fitness captured by one collapsed trace (+130k) → clipped; the `agent` attribute vs last-callable bug above.

## 6. Tooling map

- `refagents/public/` — Apache-2.0 public agents (README lists sources/scores): farm2945_v9_4, tetsutani_demand_preserving,
  ahmed_v47/v48/v53/v55/v56, alperen_first_in_line (=V48), alperen_market_rhythm, shopwork_tetsutani, **cha22**,
  multiroute_flexonafft (=cha22), masterengine3_guru (=cha22). Load with the last-callable rule.
- `eval/chassis_check.py` (head-to-head gate), `eval/pool_eval.py` (own-line pools), `eval/trace_agent.py` (frozen replays, native
  seed, shipped env), `eval/fair_env.py` (same shops for both on a seed; `apply()`/`restore()`), `tools/build_pool.py` (trace pools
  from the episode API; 429 → 8 s spacing), `tools/build_chassis_sub.py`, `tools/collect_episodes.sh`, `tools/watch_rating.sh`.
- Pools (manifests committed, replays ignored): `replays/pool` (ladder 640–1033), `replays/mid` (1500–2500), `replays/top`
  (2938–3197, rank-1's games), `replays/band2900` (2780–2960 from top-10 games), `replays/live26` (v26's live games), `replays/live28`.
- Data: `analysis/data/live/*.json` (collector), leaderboard capture with teamId+submissionId for all 9,703 teams in the old
  scratchpad (`/tmp/claude-1000/-home-iwa-working-kaggle/aec4845d-.../scratchpad/leaderboard_resp.network-response`),
  `kaggle/kaggriculture-episodes-index` (daily top-episode datasets, ~640 replays/day).
- Rust simulator (`scratchpad/kaggsim/ds/kagg`, Apache-2.0, byte-identical to 1.32.7): verified, but no speed gain for our
  1 MB Python agents; useful only for tape batches / paired A/B.
- Episode API (no auth): `POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes {"submissionId": N}`;
  replays `https://www.kaggleusercontent.com/episodes/<id>.json`.

## 7. Operational gotchas

- Never `kill $(ps | grep pattern)` where the pattern can match your own shell (it killed the session twice); filter with
  `awk '$2=="bash" && $3 ~ /script/'` or `grep "[p]ython …"`.
- Never write HANDOFF via an unquoted heredoc (backticks execute; it mangled two entries).
- Every ProcessPool that mixes fair-env and trace games must `fair_env.restore()` in the trace branch.
- Chrome with DevTools is available (`--remote-debugging-port=9222`) for the Kaggle UI (discussion/code tabs render only in JS).
- Background gates/waiters from the previous session do not survive a new session: after restarting, check the tuner logs for
  `FULL-CHECK` lines and run the 64-seed gate by hand.

## 8. Next steps, in order

1. **Watch v34 (56559582) and v35 (56595044) settle**: `.venv/bin/python analysis/scripts/ab_report.py` (ids updated); the collector
   runs with v35/v34/v33 (`collect_episodes.log` in the 1c73f37a scratchpad; kill it by pid only — a name pattern kills your shell). Expectation from the gate and the public copies' live
   scores: v33 should land ≥ 2500. If it does, the second final slot: either keep v32 (2392) or re-submit `submissions/v31_demand_g5_11.py`
   (v31 was 2411, same level — little difference), or better, a second cha22 build (e.g. `full_4_005`, a different lineage) once a gate
   shows it ≥ v33 vs v31/mirror — submitted BEFORE the final v33 copy if v33 must be the last one standing... remember only the
   order of the last two matters, not which is "first".
   If v33 settles below v32/v31 (< 2400), re-submit v31's file so the pair is v32 + v31-copy.
2. Keep reading the Code tab by score daily: if a newer public file beats cha22 8-0, it becomes the base (copies flood the swamp
   within days). `scratchpad/cha22_strength.py` / `newpub_test.py` are the templates for measuring a new file.
3. Re-run `live26_classify.py`-style loss profiles on v31/v32's latest games if their ratings drift.
4. Stop searching by 09-29 12:00 local; make sure the two files you want are the two LAST submitted before 09-30 23:59 UTC.

## 9. Post-mortem (written 2026-09-27 20:30 NZDT, before the 10-01 lock) — why this line stopped at ~2500 and what 2800+ needs

**Outcome.** Goal was 2800–3000+. Final pair: v34 + v35 (cha22 public base + gated constants), expected to settle 2400–2600, the same
band as the demand-lineage v31/v32 (2360–2410). Every offline gain (mirror 60-4 / 63-1 vs the raw file, 40-24 vs v31 vs base's 30-34)
was real and reproducible, and worth 400–800 coins per game — invisible live, because the live field at 2300–2500 is thousands of
privately tuned copies of the same public files, and games between them are ±100–700-coin sale races. v33 went 41-23 over v31
offline and plateaued at v31's level live.

**What the ladder is (measured).** 1800–2600: copies of the public route-tape files (day-12 farm census identical in 39/39 of v33's
rated games). Public frontier notebooks: 2600–2625. Nobody's copy of a public file sits above ~2650. 2600–3200: unpublished
adaptive agents (rank-1's games in `replays/top`, top-10 vs 2900-band in `replays/band2900`).

**Where the 10–20k/game gap actually is (§3b, exact cash ledgers over live replays).** NOT execution, NOT costs, NOT gross sales:
v33 sells 141k gross vs rank-1 143k and spends 23k vs 32k. The gap is net product income = unit PRICE and product MIX:
- Demand is tiny and fixed (each shop instance: 1 unit of each listed product per 4 steps; single-product shops 2; town centre
  1/product/day). Price is a pure function of market inventory (wool/melon quadratic above baseline, milk/strawberry linear, wheat/egg
  ~flat). Whatever is sold beyond demand crashes the price for BOTH players.
- The tape's farm is fixed regardless of the shop draw: ~7 sheep, ~7 cows, 33 strawberries, 0–2 tomatoes, 24 wheat. Realised prices at
  pure-sell steps: wool 92 vs rank-1 136 / top-10 170; strawberry 53 vs 148 / 123; milk 58 vs 103 / 144. Tomatoes: 2.4k vs 8.4k in the
  36/39 towns with a pizza shop or farmers' market. Wool by town: with a yarn store v33 is 17k behind (same sheep, same care: the
  race); without one it keeps 5.6 sheep for wool sold at 2/unit (top-10: 3.6 → 1.6 by day 28).
- The top agents hire the same ~10 hands/day and use the same tiles; they allocate them to what the town buys and drip-sell to
  inventory (rank-1: 1.7 wool units per order, whole stock sold 16% of the time vs our 72%).

**Add-ons tested on the tape, all rejected with numbers (§3b, §5).** Sale-hold gate −10k (holding gifts the opponent ~+24k in a shared
market). Sheep cut in no-yarn towns ≈ +200/game, win-rate neutral or worse. Tomato swap of the day-11 batch −8k. Replant layer
infeasible: the tape leaves 1–11 idle hand-steps/day (end-of-day tails 0–1 per hand), 1–5 free tiles mid-game, and extra hands cost
fib(n) = 89/144 per day → net 0 to +500. Sale-slot shuffle −2k, horizon jitter noise, clone blinding ties, RL silver at best (others).
Lesson: a route-tape cannot be edited piecemeal — its labour, cash flow, shed and sale plan all assume the fixed farm.

**Why "our own agent" lost before (§5).** From the tape's own day-11 farm vs a passive opponent the tape makes 137k; our executor
(`kaggriculture/agents/market.py` planner + `tour.py`/`hybrid.py`) made 106–113k — the plan side was fine, execution lost 25–30k.
The own line rated ~800 live.

**Spec for the 2800+ agent (what the measurements say it must do).**
1. Read `town.unlocked_shops` every 3 days and set production to demand: sheep only with a yarn store (add them when it appears,
   ~day 11 on average), tomatoes (~10 tiles from day 16, replanted) with pizza/farmers' market, geese for bakery/brunch (egg price is
   glut-proof), strawberries wound down after day 20, 25–30 wheat late. Stop feeding animals whose product has no shop (they escape
   after 2 unfed days).
2. Sell to inventory, not to schedule: small lots when inventory ≤ baseline (price ≥ base), never dump; against a dumping copy this
   only pays if your production is already sized to demand (otherwise you just hold a glut).
3. Execution at tape quality: 10 hands/day at fib cost, no idle tails, routes that end near the shed (hands auto-drop at day end),
   water every plant daily, harvest before max_held caps (goose 4, sheep 6, cow 6), fertiliser on watered days only.
4. Opening: the tape's day 0–11 is not the gap (d0–9 revenue 8.8k vs top-10 9.2k); reuse it (hybrid) and take over from day 12.
5. Evaluate against the right field: the live 2300–2500 opponents are privately tuned copies, not the raw public files; gate against
   your own tuned variants and against live replays with `fair_env.restore()`, and expect offline edges among copies to vanish live.
   Target a consistent +3–5k margin over copies (the top-10 beat the 2900 band 17-7 by +5k); that is what an 80–90% win rate and
   2700+ look like.

**What to reuse.** `analysis/scripts/{income_gap,cash_ledger,demand_vs_supply,sale_quality,wool_gap,labour_audit,idle_structure}.py`
(replay analytics), `eval/chassis_check.py` + `analysis/scripts/genome_h2h.py` + `verify_build.py` (gate/verify), `refagents/public/`
(13 public agents, last-callable rule), `replays/{top,band2900,live_*}` (the field), the engine notes in §3b.
