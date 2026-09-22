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
