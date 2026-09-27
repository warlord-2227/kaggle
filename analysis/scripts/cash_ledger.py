"""Exact-ish cash ledger per player from live replays. Action at steps[t+1] is the one applied between obs t and t+1.
Known costs from engine rules: seeds (CROPS seed price), animals (ANIMALS cost), hires (fib(hires_today)), land (1000/2000/4000).
Residual per step = sells - product buys, split by qty x town price when both occur. Also counts FEED / PLANT / DIG hand+farmer
actions. Same replay groups as income_gap.py. Usage: .venv/bin/python analysis/scripts/cash_ledger.py [jobs]"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT, PRODUCTS
SEED = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}; ANIMAL = {"GOOSE": 300, "COW": 400, "SHEEP": 500}; LAND = [1000, 2000, 4000]
def fib(n):
    a, b = 1, 1
    for _ in range(n): a, b = b, a + b
    return a
def analyse(job):
    path, idx, label = job
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    L = collections.defaultdict(float); acts = collections.Counter(); land_n = 0
    for t in range(719):
        o = steps[t][0]["observation"]; ph = min(o["day"] // 10, 2); prices = o["market"]["prices"]
        m0 = o["farms"][idx]["money"]; m1 = steps[t + 1][0]["observation"]["farms"][idx]["money"]; delta = m1 - m0
        a = steps[t + 1][idx].get("action") or {}
        orders = [m for m in (a.get("market") or []) if isinstance(m, (list, tuple)) and m]
        hires_today = o["farms"][idx]["hires_today"]; known = 0.0; sells = collections.Counter(); buys = collections.Counter()
        for m in orders:
            if m[0] == "HIRE": known += fib(hires_today); hires_today += 1; L["hire"] += fib(hires_today - 1); acts["HIRE"] += 1
            elif m[0] == "BUY_LAND":
                if land_n < 3: known += LAND[land_n]; L["land"] += LAND[land_n]; land_n += 1
            elif len(m) >= 3 and isinstance(m[2], (int, float)):
                if m[0] == "BUY_SEED" and m[1] in SEED: known += m[2] * SEED[m[1]]; L["seed_" + m[1]] += m[2] * SEED[m[1]]; acts["seed_" + m[1]] += m[2]
                elif m[0] == "BUY_ANIMAL" and m[1] in ANIMAL: known += m[2] * ANIMAL[m[1]]; L["animal_" + m[1]] += m[2] * ANIMAL[m[1]]; acts["animal_" + m[1]] += m[2]
                elif m[0] == "SELL": sells[m[1]] += m[2] * prices.get(m[1], 0); acts["sell_" + m[1]] += m[2]
                elif m[0] == "BUY_PRODUCT": buys[m[1]] += m[2] * prices.get(m[1], 0); acts["buy_" + m[1]] += m[2]
        resid = delta + known   # = actual sells - actual buys
        S, B = sum(sells.values()), sum(buys.values())
        if S and not B: tot = resid; [L.__setitem__(f"sell_{p}@{ph}", L[f"sell_{p}@{ph}"] + tot * v / S) for p, v in sells.items()]
        elif B and not S: tot = -resid; [L.__setitem__(f"buy_{p}", L[f"buy_{p}"] + tot * v / B) for p, v in buys.items()]
        elif S and B:
            # scale both estimates by a common factor so they net to resid (fallback: keep estimates)
            k = resid / (S - B) if abs(S - B) > 1e-6 and (resid / (S - B)) > 0 else 1.0
            for p, v in sells.items(): L[f"sell_{p}@{ph}"] += v * k
            for p, v in buys.items(): L[f"buy_{p}"] += v * k
        elif abs(resid) > 0.5: L["unexplained"] += resid
        for h in (a.get("hands") or []) + [a.get("farmer") or []]:
            for x in h:
                v = x[0] if isinstance(x, (list, tuple)) else x
                if v in ("FEED", "PLANT", "DIG", "HARVEST", "FERTILIZE", "WATER", "COLLECT_FERTILIZER"): acts[v] += 1
    return dict(label=label, final=R["rewards"][idx], L=dict(L), acts=dict(acts))
if __name__ == "__main__":
    J = jobs()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/cash_ledger.json", "w"))
    G = collections.defaultdict(list)
    for r in res: G[r["label"]].append(r)
    labels = [l for l in ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"] if G[l]]
    def mean(lab, f): return st.mean(f(r) for r in G[lab])
    def L(lab, k): return mean(lab, lambda r: r["L"].get(k, 0))
    print("== balance check: 3000 + sells - buys - seeds - animals - hire - land + unexplained vs final")
    for lab in labels:
        sells = sum(L(lab, k) for k in {k for r in G[lab] for k in r["L"] if k.startswith("sell_")}); buys = sum(L(lab, k) for k in {k for r in G[lab] for k in r["L"] if k.startswith("buy_")})
        seeds = sum(L(lab, k) for k in {k for r in G[lab] for k in r["L"] if k.startswith("seed_")}); an = sum(L(lab, k) for k in {k for r in G[lab] for k in r["L"] if k.startswith("animal_")})
        print(f"{lab:10s} n={len(G[lab]):2d} final {mean(lab, lambda r: r['final']):8,.0f} | sells {sells:8,.0f} buys {buys:7,.0f} seeds {seeds:6,.0f} animals {an:6,.0f} hire {L(lab,'hire'):6,.0f} land {L(lab,'land'):6,.0f} unexpl {L(lab,'unexplained'):7,.0f} | check {3000 + sells - buys - seeds - an - L(lab,'hire') - L(lab,'land') + L(lab,'unexplained'):8,.0f}")
    print("\n== NET by product (sells − product buys), all days; then sells by phase")
    print(f"{'group':10s} " + " ".join(f"{p[:6]:>8s}" for p in PRODUCTS))
    for lab in labels:
        print(f"{lab:10s} " + " ".join(f"{sum(L(lab, f'sell_{p}@{ph}') for ph in range(3)) - L(lab, 'buy_' + p):8,.0f}" for p in PRODUCTS))
    print("\n== sells by product x phase (d0-9/d10-19/d20-29)")
    for lab in labels:
        print(f"{lab:10s} " + " ".join(f"{p[:5]} " + "/".join(f"{L(lab, f'sell_{p}@{ph}'):,.0f}" for ph in range(3)) for p in PRODUCTS if p != "FERTILIZER"))
    print("\n== costs: seeds by crop / animals / product buys / hire / land")
    ck = ["seed_WHEAT", "seed_CARROT", "seed_TOMATO", "seed_STRAWBERRY", "seed_MELON", "animal_GOOSE", "animal_COW", "animal_SHEEP", "buy_WHEAT", "buy_FERTILIZER", "hire", "land"]
    print(f"{'group':10s} " + " ".join(f"{k[-9:]:>9s}" for k in ck))
    for lab in labels: print(f"{lab:10s} " + " ".join(f"{L(lab, k):9,.0f}" for k in ck))
    print("\n== action counts: units bought (wheat/fert), FEED, PLANT, DIG, HARVEST, FERTILIZE, COLLECT_FERTILIZER, hires, seed units")
    ak = ["buy_WHEAT", "buy_FERTILIZER", "FEED", "PLANT", "DIG", "HARVEST", "FERTILIZE", "COLLECT_FERTILIZER", "HIRE", "seed_WHEAT", "seed_STRAWBERRY", "seed_TOMATO", "seed_CARROT"]
    print(f"{'group':10s} " + " ".join(f"{k[-9:]:>9s}" for k in ak))
    for lab in labels: print(f"{lab:10s} " + " ".join(f"{mean(lab, lambda r, k=k: r['acts'].get(k, 0)):9,.0f}" for k in ak))
