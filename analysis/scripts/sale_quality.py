"""Sale quality per player: for each SELL order (action at steps[t+1] applied between obs t and t+1): units, quoted town price at obs t,
realised per-unit price (money delta / units when the step has only SELL orders), market inventory at sale, and whether the order
was the whole shed stock. Aggregated per group and product. Usage: .venv/bin/python analysis/scripts/sale_quality.py [jobs]"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT, PRODUCTS
def analyse(job):
    path, idx, label = job
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    rows = []
    for t in range(719):
        o = steps[t][0]["observation"]; prices = o["market"]["prices"]; inv = o["market"]["inventory"]
        a = steps[t + 1][idx].get("action") or {}
        orders = [m for m in (a.get("market") or []) if isinstance(m, (list, tuple)) and m]
        sells = [m for m in orders if m[0] == "SELL" and len(m) >= 3 and isinstance(m[2], (int, float))]
        if not sells or len(sells) != len(orders): continue   # only pure-sell steps -> realised price is exact
        m0 = o["farms"][idx]["money"]; m1 = steps[t + 1][0]["observation"]["farms"][idx]["money"]; d = m1 - m0
        shed0 = steps[t][idx]["observation"]["private"]["shed"]; shed1 = steps[t + 1][idx]["observation"]["private"]["shed"]
        # actual filled units = shed decrease (deposits in the same step would understate; rare at pure-sell steps)
        filled = {m[1]: max(0, shed0.get(m[1], 0) - shed1.get(m[1], 0)) for m in sells}
        units = sum(filled.values()); quoted = sum(filled[m[1]] * prices.get(m[1], 0) for m in sells)
        if units <= 0 or quoted <= 0 or d <= 0: continue
        for m in sells:
            u = filled[m[1]]
            if u <= 0 or prices.get(m[1], 0) <= 0: continue
            share = u * prices.get(m[1], 0) / quoted
            rows.append(dict(p=m[1], units=u, ordered=m[2], quoted=prices.get(m[1], 0), realised=d * share / u, inv=inv.get(m[1], 0), day=o["day"], hour=o["hour"], step=t,
                             whole=(shed0.get(m[1], 0) <= u), nsell=len(sells)))
    return dict(label=label, rows=rows)
if __name__ == "__main__":
    J = jobs()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    G = collections.defaultdict(list)
    for r in res: G[r["label"]] += r["rows"]
    labels = [l for l in ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"] if G[l]]
    print("== per product (FILLED units from shed deltas): orders, mean units/order, mean quoted price, realised/quoted, realised per unit, mean inventory at sale, share of orders selling whole stock")
    for p in ["WOOL", "STRAWBERRY", "MILK", "EGG", "TOMATO", "WHEAT", "CARROT", "MELON"]:
        print(f"-- {p}")
        for lab in labels:
            r = [x for x in G[lab] if x["p"] == p]
            if len(r) < 5: continue
            U = sum(x["units"] for x in r)
            Q = sum(x['quoted']*x['units'] for x in r) or 1
            print(f"   {lab:10s} orders {len(r):5d} units/order {U/len(r):5.1f} quoted {st.mean(x['quoted'] for x in r):6.0f} realised/quoted {sum(x['realised']*x['units'] for x in r)/Q:5.2f} realised/unit {sum(x['realised']*x['units'] for x in r)/(U or 1):6.0f} inv {st.mean(x['inv'] for x in r):7.0f} whole {st.mean(x['whole'] for x in r):.2f}")
    print("\n== units-per-order distribution (all products) and hour-of-day of sales")
    for lab in labels:
        r = G[lab]; u = sorted(x["units"] for x in r); hrs = collections.Counter(x["hour"] for x in r)
        print(f"{lab:10s} orders {len(r)} units p50 {u[len(u)//2]} p90 {u[int(len(u)*.9)]} max {u[-1]} | hours top {hrs.most_common(6)}")
