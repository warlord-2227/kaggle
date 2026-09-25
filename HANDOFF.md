# Kaggriculture — session handoff (2026-09-25, 19:20 local / 07:20 UTC)

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
| **v31** 56508691 | `submissions/v31_demand_g5_11.py` | demand-preserving public file + search-tuned constants (run 5) | **2444 @ ~140 games** (peak 2526) | **active, final #1** |
| **v32** 56515072 | `submissions/v32_demand_g6_29.py` | same + run-6 constants | 2430 @ ~120 | active, final #2 |
| v30 56495224 | `v30_demand_g4_17.py` | run-4 constants | 2337 (retired) | |
| v29 56493719 | `v29_demand_base_again.py` | unmodified demand file (same-field control) | 2109 (retired) | |
| v26 56453495 | `v26_demand_base.py` | unmodified demand file, 2 days earlier | 2378 (retired) | field was weaker then |
| v23 56446174 | our own market agent | 783 | | own line parked |

Same-field A/B at game 60: v31 2498 / v30 2194 / v29 (base) 2088 → the constants search moved the ladder +300–400 over the
unmodified file; v32 vs v31 was inside the noise (2383 vs 2498 @60). Bronze line ≈ 2450; 3000+ needs a different species
(see §5). **5 submission slots are available today (UTC day since 12:00 local); none spent.**

## 3. The ladder, as measured

- 1800–2550 is a swamp of copies of the public route-tape chassis (127 of v26's 134 opponents ≥2200; 82 with our exact opening).
  Games between copies are decided by sale races and SELL-slot order (±$1k). Copies rated 2500+ beat v26 8-2.
- 2500–2960 = adaptive farms (diverse; ~10 tomato tiles d14–20, strawberries wound down from d20, 25–30 wheat late). The
  top-10 beat that band 17-7 by +5k. Frozen replays of them lose to the chassis 33-7; live they win → their edge is reaction.
- **The public frontier moves every few days.** Score order on the Code tab now: V38 2625, V39 2621, V53 2597, V55 2596,
  Multi-Route 2584, Kaggricult-Man 2579, cha22 2568, Master Engine V3 2544. `cha22.py` (= Multi-Route = Master Engine V3,
  byte-identical, entry `ig_agent`, 7,482 lines, same lineage + EXP239–241 learned route choice) beats the demand file **8-0
  +3.2k**, V56 8-0, farm2945 8-0 and our v31 **7-5 −1.0k** → it is the new base (§4).

## 4. Current work: constants search on the cha22 base → v33

- Tuner: `experiments/evolve_chassis.py` (`CHASSIS=cha22`, 77 auto-derived knobs = the file's top-level numeric/bool constants,
  applied by setattr on a fresh import; `make_agent` returns the LAST callable — bug fixed 09-25 18:05, all earlier cha22 numbers
  void). Fitness = paired WIN RATE (margin tiebreak, clipped ±10k) vs mirror ×3 seeds + demand/v56/**v31** ×3 seeds + 2 rotating
  relatives + 4 diverse frozen traces (`replays/{mid,band2900,live26}`, shipped env via `fair_env.restore()`).
- Running now: run 3 (`JOBS=16`, log scratchpad `evolve_chassis_cha22_3.log`, gen ~8, +1.4k vs demand, +0.1k vs v31 so far) and
  run 4 (`JOBS=6`, `evolve_chassis_cha22_4.log`). Elites: `experiments/evolve_chassis_cha22_best.json`, full checks every 6 gens
  `experiments/evolve_chassis_cha22_full_<run>_<gen>.json`.
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
- Live monitoring: `tools/watch_rating.sh <ids…>` (40 × 10 min; restart when it ends — it is NOT running now),
  `tools/collect_episodes.sh` (running, saves ListEpisodes JSON to `analysis/data/live/`), same-field A/B report
  scratchpad `ab_report.py` (edit the ids at the bottom), classifier `live26_classify.py` (clone vs adaptive by day-12 farm).

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

1. When run 3/4 print `FULL-CHECK gen 11` (and every 6 gens after), run the gate (§4) on the newest
   `experiments/evolve_chassis_cha22_full_*.json`; promote the first elite that passes as **v33**; then decide the second final.
2. Keep reading the Code tab by score daily: if a newer public file beats cha22 8-0, it becomes the base (copies flood the swamp
   within days). `scratchpad/cha22_strength.py` / `newpub_test.py` are the templates for measuring a new file.
3. Re-run `live26_classify.py`-style loss profiles on v31/v32's latest games if their ratings drift.
4. Stop searching by 09-29 12:00 local; make sure the two files you want are the two LAST submitted before 09-30 23:59 UTC.
