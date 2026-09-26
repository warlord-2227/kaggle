# Public Kaggriculture agents (Apache-2.0), used as reactive sparring opponents

| file | source notebook | author | live ladder score |
|---|---|---|---|
| farm2945_v9_4.py | kaggle.com/code/thomastschinkel/the-2945-farm-96-vs-the-top-10-public-bots (output main.py, pulled 2026-09-22) | thomastschinkel (+ upstream chain, notices in file) | 2944.7 (sub 56269928) |
| shopwork_tetsutani.py | kaggle.com/code/tetsutani/shape-the-shop-work-the-pasture-kaggriculture (output main.py, pulled 2026-09-22) | tetsutani | 2248 |

Kaggle loads the *last callable* in main.py; both files end with `agent` re-inserted last, so `module.agent` is the entry point.
Load with `refagents.public.load(name)` or importlib; do not edit these files (byte-exact copies of the published outputs).

Added 2026-09-22 15:20 (all Apache-2.0 notebook outputs, byte-exact):
ahmed_v47.py / ahmed_v48.py / ahmed_v56.py = ahmedberatozer/kaggriculture-v47-reactive-market-coordination (2686), -v48-clear-the-queue (2670), -v56-smarter-seeds-and-fertilizer (newest);
tetsutani_demand_preserving.py = tetsutani/demand-preserving-turn-sale-timing (2750.2, best public on 09-19);
alperen_first_in_line.py = alperen5252525/kaggriculture-first-in-line-stock-into-income (2746); alperen_market_rhythm.py = alperen5252525/kaggriculture-market-rhythm-sale-policy.

Added 2026-09-25 (Code tab sorted by score; all Apache-2.0 notebook outputs): ahmed_v53.py (V53 Opening Signature, 2597),
ahmed_v55.py (V55 One-Turn Market Race Edge, 2596), cha22.py (abhinav0370/cha22-agent, 2568), multiroute_flexonafft.py
(flexonafft/kaggriculture-multi-route-farming-agent, 2584), masterengine3_guru.py (guruprasaathas111/kaggriculture-master-engine-v3, 2544).

Added 2026-09-25 23:20 (Code tab by score; all V39/v9-layer lineage with Apache-2.0 notices; 89-92% of code lines shared with cha22):
ahmed_v34.py (v34 Observed Market Timing, 2601.6), ahmed_v41.py (V41 Review Candidate, 2586.4), masterengine_v53e_guru.py
(guruprasaathas111/kaggriculture-master-engine-v53e01d74d8f, 2581), marketshock_m1_leoprovorov.py (Kaggricult-Man, 2579.4; agent file
`marketshock_m1_wr1_main.py` from dataset leoprovorov/marketshock-m1-wr1-agent, sha256 853472b4…), arsgorynich_v43.py (V43 Local Confirmed,
2550.5; main.py from the notebook's base64 tar), arsgorynich_herdsafe_v3.py (Herd Safe v3, 2513.3; zlib/b85-packed in the notebook).
Master Engine V3 re-run 2026-09-25 (score 2515.9) is byte-identical to cha22.py (packed as SOURCE_BYTES with a sha256 check).
Measured 2026-09-25 23:27 (`analysis/scripts/newpub_vs_cha22.py`, cha22 vs each, 12 paired seeds 601-612, same shops): v34 12-0 +9.2k,
v41 12-0 +6.5k, me53e 12-0 +6.5k, v43 12-0 +5.7k, herdsafe3 10-2 +2.3k. marketshock via its last callable (a patch factory) plays
nothing (3,000 coins); see below for its `agent` entry. cha22 remains the base.
marketshock via `module.agent` (the wrapped stack): cha22 11-1 +3.2k (12 seeds). Closest relatives to cha22 are herdsafe3 (+2.3k) and
marketshock (+3.2k) → candidates for extra gate opponents.
