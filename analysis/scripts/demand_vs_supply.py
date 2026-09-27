"""Per game and product: town demand capacity (shop instances carrying it x 6/day x mult + 1/day town centre, integrated over the
days each shop was unlocked) vs units each player sold, and realised price per unit. Usage: .venv/bin/python analysis/scripts/demand_vs_supply.py [jobs]"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT
SHOPS = {"BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"], "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
         "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"], "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]}
P = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"]
def analyse(job):
    path, idx, label = job
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    demand = collections.Counter(); 
    for t in range(0, 720, 4):
        shops = steps[t][0]["observation"]["town"].get("unlocked_shops", [])
        for s in shops:
            pr = SHOPS[s]; mult = 2 if len(pr) == 1 else 1
            for p in pr: demand[p] += mult
        if t % 24 == 0:
            for p in P: demand[p] += 1
    sold = collections.Counter(); rev = collections.Counter(); both = collections.Counter()
    for t in range(719):
        o = steps[t][0]["observation"]; prices = o["market"]["prices"]
        for i in (0, 1):
            a = steps[t + 1][i].get("action") or {}
            for m in (a.get("market") or []):
                if isinstance(m, (list, tuple)) and m and m[0] == "SELL" and len(m) >= 3 and isinstance(m[2], (int, float)):
                    both[m[1]] += m[2]
                    if i == idx: sold[m[1]] += m[2]; rev[m[1]] += m[2] * prices.get(m[1], 0)
    endshops = steps[-1][0]["observation"]["town"].get("unlocked_shops", [])
    return dict(label=label, demand=dict(demand), sold=dict(sold), both=dict(both), rev=dict(rev), shops=endshops, final=R["rewards"][idx])
if __name__ == "__main__":
    J = jobs()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/demand_vs_supply.json", "w"))
    G = collections.defaultdict(list)
    for r in res: G[r["label"]].append(r)
    labels = [l for l in ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"] if G[l]]
    print("== mean per game: town demand capacity D (units over the game) | units sold by this player S | by both players B | S/D | quoted-price revenue/unit")
    for p in P:
        print(f"-- {p}")
        for lab in labels:
            r = G[lab]; D = st.mean(x["demand"].get(p, 0) for x in r); S = st.mean(x["sold"].get(p, 0) for x in r); B = st.mean(x["both"].get(p, 0) for x in r)
            U = sum(x["sold"].get(p, 0) for x in r); RV = sum(x["rev"].get(p, 0) for x in r)
            print(f"   {lab:10s} D {D:6.0f}  S {S:6.0f}  B {B:6.0f}  S/D {S / D if D else 0:5.2f}  B/D {B / D if D else 0:5.2f}  quoted/unit {RV / U if U else 0:6.0f}")
    print("\n== how often the product's shop is absent from the town (end of game) and what the player still sold of it")
    for p, shopset in (("WOOL", {"YARN_STORE"}), ("TOMATO", {"PIZZA_SHOP", "FARMERS_MARKET"}), ("CARROT", {"PET_CAFE", "FARMERS_MARKET"}), ("MILK", {"PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"})):
        for lab in labels:
            r = G[lab]; absent = [x for x in r if not (set(x["shops"]) & shopset)]
            print(f"   {p:10s} {lab:10s} shop absent in {len(absent)}/{len(r)} games; units sold when absent {st.mean(x['sold'].get(p, 0) for x in absent) if absent else 0:5.0f} vs present {st.mean(x['sold'].get(p, 0) for x in r if x not in absent) if len(absent) < len(r) else 0:5.0f}")
