"""Spending decomposition from live replays: negative money deltas attributed to the market actions in the same step
(HIRE, BUY_SEED by crop, BUY_PRODUCT by product, BUY_ANIMAL, BUY_LAND), plus 'unexplained' (no market action in the step).
Same replay groups as income_gap.py. Usage: .venv/bin/python analysis/scripts/spend_gap.py [jobs]"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT
def analyse(job):
    path, idx, label = job
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    spend = collections.defaultdict(float); cnt = collections.defaultdict(float); gross_pos = 0.0; gross_neg = 0.0
    byphase = [collections.defaultdict(float) for _ in range(3)]
    for t in range(719):
        o = steps[t][0]["observation"]; prices = o["market"]["prices"]; ph = min(o["day"] // 10, 2)
        m0 = o["farms"][idx]["money"]; m1 = steps[t + 1][0]["observation"]["farms"][idx]["money"]; d = m1 - m0
        a = steps[t][idx].get("action") or {}; acts = [m for m in (a.get("market") or []) if isinstance(m, (list, tuple)) and m]
        keys = []
        for m in acts:
            if m[0] == "HIRE": keys.append("HIRE"); cnt["HIRE"] += 1
            elif m[0] == "BUY_LAND": keys.append("LAND"); cnt["LAND"] += 1
            elif m[0] == "BUY_SEED" and len(m) >= 3: keys.append("SEED_" + m[1]); cnt["SEED_" + m[1]] += m[2]
            elif m[0] == "BUY_ANIMAL" and len(m) >= 3: keys.append("ANIMAL_" + m[1]); cnt["ANIMAL_" + m[1]] += m[2]
            elif m[0] == "BUY_PRODUCT" and len(m) >= 3: keys.append("PROD_" + m[1]); cnt["PROD_" + m[1]] += m[2]; cnt["PRODCOST_" + m[1]] += m[2] * prices.get(m[1], 0)
        if d > 0: gross_pos += d
        elif d < 0:
            gross_neg += -d
            if not keys: spend["unexplained"] += -d; byphase[ph]["unexplained"] += -d
            else:
                # split evenly across the buy-type keys present in the step (approximation)
                for k in keys: spend[k] += -d / len(keys); byphase[ph][k] += -d / len(keys)
    return dict(label=label, final=R["rewards"][idx], gross_pos=gross_pos, gross_neg=gross_neg, spend=dict(spend), cnt=dict(cnt), byphase=[dict(b) for b in byphase])
if __name__ == "__main__":
    J = jobs()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/spend_gap.json", "w"))
    G = collections.defaultdict(list)
    for r in res: G[r["label"]].append(r)
    labels = ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"]
    keys = sorted({k for r in res for k in r["spend"]}, key=lambda k: -sum(r["spend"].get(k, 0) for r in res))
    def mean(lab, f): v = [f(r) for r in G[lab]]; return st.mean(v) if v else float("nan")
    print(f"{'group':10s} {'n':>3s} {'final':>8s} {'gross+':>8s} {'gross-':>8s} | " + " ".join(f"{k[:11]:>11s}" for k in keys[:12]))
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} {len(G[lab]):3d} {mean(lab, lambda r: r['final']):8,.0f} {mean(lab, lambda r: r['gross_pos']):8,.0f} {mean(lab, lambda r: r['gross_neg']):8,.0f} | " + " ".join(f"{mean(lab, lambda r, k=k: r['spend'].get(k, 0)):11,.0f}" for k in keys[:12]))
    print("\n== counts (hires, land, seed units by crop, animals, product units bought)")
    ck = sorted({k for r in res for k in r["cnt"] if not k.startswith("PRODCOST_")}, key=lambda k: -sum(r["cnt"].get(k, 0) for r in res))
    print(f"{'group':10s} " + " ".join(f"{k[:11]:>11s}" for k in ck[:14]))
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} " + " ".join(f"{mean(lab, lambda r, k=k: r['cnt'].get(k, 0)):11,.0f}" for k in ck[:14]))
    print("\n== spend by phase (d0-9 / d10-19 / d20-29) for the top keys")
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} " + " | ".join(f"{k[:8]} " + "/".join(f"{mean(lab, lambda r, k=k, p=p: r['byphase'][p].get(k, 0)):,.0f}" for p in range(3)) for k in keys[:6]))
