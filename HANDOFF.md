# Kaggriculture — session handoff (2026-09-26, 08:30 local / 09-25 20:30 UTC)

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
| **v34** 56559582 | `submissions/v34_cha22_g4_17.py` | **cha22 base + run-4 gen-17 constants** (genome `experiments/v34_cha22_genome.json`) | submitted 09-26 08:22 local (09-25 20:22 UTC) | **active** |
| **v33** 56553451 | `submissions/v33_cha22_g3_17.py` | **cha22 base + run-3 gen-17 constants** (genome `experiments/v33_cha22_genome.json`) | 2124 @ 74 (67-6 vs <2200, all chassis copies; still climbing) | **active** |
| v32 56515072 | `submissions/v32_demand_g6_29.py` | demand-preserving + run-6 constants | 2367 @ 202 | retired by v34 |
| v31 56508691 | `submissions/v31_demand_g5_11.py` | demand-preserving + run-5 constants | 2411 @ ~200 (peak 2526; 28-40 vs 2500+) | retired by v33; re-submit it if v33 disappoints |
| v30 56495224 | `v30_demand_g4_17.py` | run-4 constants | 2337 (retired) | |
| v29 56493719 | `v29_demand_base_again.py` | unmodified demand file (same-field control) | 2109 (retired) | |
| v26 56453495 | `v26_demand_base.py` | unmodified demand file, 2 days earlier | 2378 (retired) | field was weaker then |
| v23 56446174 | our own market agent | 783 | | own line parked |

Same-field A/B at game 60: v31 2498 / v30 2194 / v29 (base) 2088 → the constants search moved the ladder +300–400 over the
unmodified file; v32 vs v31 was inside the noise (2383 vs 2498 @60). v31/v32 both settled at **~2400** (their 50% band). Bronze line
≈ 2450; 3000+ needs a different species (see §5). 3 submission slots left in the current UTC day (resets 12:00 local 09-26). **Active pair = v33 + v34, both cha22 builds.**

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

## 4. Current work: constants search on the cha22 base → v33

- Tuner: `experiments/evolve_chassis.py` (`CHASSIS=cha22`, 77 auto-derived knobs = the file's top-level numeric/bool constants,
  applied by setattr on a fresh import; `make_agent` returns the LAST callable — bug fixed 09-25 18:05, all earlier cha22 numbers
  void). Fitness = paired WIN RATE (margin tiebreak, clipped ±10k) vs mirror ×3 seeds + demand/v56/**v31** ×3 seeds + 2 rotating
  relatives + 4 diverse frozen traces (`replays/{mid,band2900,live26}`, shipped env via `fair_env.restore()`).
- Running now (pids from 09-25 ~18:05, survive sessions): run 3 (`JOBS=16`, log
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

1. **Watch v33 (56553451) and v34 (56559582) settle**: `.venv/bin/python analysis/scripts/ab_report.py` (ids updated); the collector
   runs with v34/v33/v32/v31 (`collect_episodes.log` in the 1c73f37a scratchpad; kill it by pid only — a name pattern kills your shell). Expectation from the gate and the public copies' live
   scores: v33 should land ≥ 2500. If it does, the second final slot: either keep v32 (2392) or re-submit `submissions/v31_demand_g5_11.py`
   (v31 was 2411, same level — little difference), or better, a second cha22 build (e.g. `full_4_005`, a different lineage) once a gate
   shows it ≥ v33 vs v31/mirror — submitted BEFORE the final v33 copy if v33 must be the last one standing... remember only the
   order of the last two matters, not which is "first".
   If v33 settles below v32/v31 (< 2400), re-submit v31's file so the pair is v32 + v31-copy.
2. Keep reading the Code tab by score daily: if a newer public file beats cha22 8-0, it becomes the base (copies flood the swamp
   within days). `scratchpad/cha22_strength.py` / `newpub_test.py` are the templates for measuring a new file.
3. Re-run `live26_classify.py`-style loss profiles on v31/v32's latest games if their ratings drift.
4. Stop searching by 09-29 12:00 local; make sure the two files you want are the two LAST submitted before 09-30 23:59 UTC.
