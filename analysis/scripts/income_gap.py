"""Income-stream gap analysis from live replays: per player, revenue by product x phase (est. qty x town price, rescaled to the true
positive money deltas), units sold, tile census by day, hires. Groups: rank1 / rank1-opp (replays/top), top10 / band2900
(replays/band2900), v33 / copies (replays/live_56553451). Usage: .venv/bin/python analysis/scripts/income_gap.py [jobs]"""
import json, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT = "/home/iwa/working/kaggle"
PRODUCTS = ["WHEAT", "CARROT", "STRAWBERRY", "TOMATO", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
PHASES = [(0, 10), (10, 20), (20, 30)]
DAYS = [8, 12, 16, 20, 24, 28]
def census(farm):
    cr = collections.Counter(); an = collections.Counter(); n = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                n += 1
                if t.get("animal"): an[t["animal"]] += 1
                elif t.get("kind") == "PLANT": cr[t["crop"]] += 1
    return cr, an, n
def analyse(job):
    path, idx, label = job
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    out = dict(label=label, path=os.path.basename(path), idx=idx, final=R["rewards"][idx])
    est = collections.defaultdict(float); units = collections.defaultdict(float); truepos = [0.0] * 3
    buys = collections.defaultdict(float); hires = 0; land = 0
    for t in range(719):
        o = steps[t][0]["observation"]; day = o["day"]; ph = min(day // 10, 2)
        prices = o["market"]["prices"]
        m0 = steps[t][0]["observation"]["farms"][idx]["money"]; m1 = steps[t + 1][0]["observation"]["farms"][idx]["money"]
        a = steps[t][idx].get("action") or {}
        for m in (a.get("market") or []):
            if not isinstance(m, (list, tuple)) or not m: continue
            if m[0] == "SELL" and len(m) >= 3:
                est[(m[1], ph)] += m[2] * prices.get(m[1], 0); units[(m[1], ph)] += m[2]
            elif m[0] in ("BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(m) >= 3: buys[m[0]] += 1
            elif m[0] == "HIRE": hires += 1
            elif m[0] == "BUY_LAND": land += 1
        if m1 > m0: truepos[ph] += m1 - m0
    # rescale est per phase to true positive deltas
    rev = {}
    for ph in range(3):
        e = sum(v for (p, q), v in est.items() if q == ph); k = truepos[ph] / e if e > 0 else 0
        for p in PRODUCTS: rev[(p, ph)] = est.get((p, ph), 0) * k
    out["rev"] = {f"{p}@{ph}": rev[(p, ph)] for p in PRODUCTS for ph in range(3)}
    out["units"] = {f"{p}@{ph}": units.get((p, ph), 0) for p in PRODUCTS for ph in range(3)}
    out["truepos"] = truepos; out["hires"] = hires; out["land"] = land; out["buys"] = dict(buys)
    cen = {}
    for d in DAYS:
        cr, an, n = census(steps[d * 24 + 23][0]["observation"]["farms"][idx]); cen[d] = dict(cr=dict(cr), an=dict(an), tiles=n)
    out["census"] = cen
    fin = steps[-1][0]["observation"]["farms"][idx]; out["hands_end"] = len(fin["hands"]); out["quads"] = len(fin["unlocked_quadrants"])
    return out
def jobs():
    J = []
    for m in json.load(open(ROOT + "/replays/top/manifest.json")):
        p = f"{ROOT}/replays/top/episode-{m['ep']}-replay.json"
        if os.path.exists(p): J += [(p, 1 - m["opp_idx"], "rank1"), (p, m["opp_idx"], "rank1-opp")]
    for m in json.load(open(ROOT + "/replays/band2900/manifest.json")):
        p = f"{ROOT}/replays/band2900/episode-{m['ep']}-replay.json"
        if os.path.exists(p): J += [(p, 1 - m["opp_idx"], "top10"), (p, m["opp_idx"], "band2900")]
    d = json.load(open(ROOT + "/analysis/data/live/56553451.json"))
    for e in d["episodes"]:
        p = f"{ROOT}/replays/live_56553451/episode-{e['id']}-replay.json"
        if e.get("state") != "COMPLETED" or not os.path.exists(p): continue
        mi = next(i for i, x in enumerate(e["agents"]) if x["submissionId"] == 56553451)
        J += [(p, mi, "v33"), (p, 1 - mi, "copies")]
    return J
if __name__ == "__main__":
    J = jobs(); print("replay-sides:", collections.Counter(l for _, _, l in J), flush=True)
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/income_gap.json", "w"))
    G = collections.defaultdict(list)
    for r in res: G[r["label"]].append(r)
    labels = ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"]
    def mean(lab, f): v = [f(r) for r in G[lab]]; return st.mean(v) if v else float("nan")
    print("\n== final coins / revenue by phase (true positive deltas) / hires / land / hands / quadrants")
    print(f"{'group':10s} {'n':>3s} {'final':>8s} {'d0-9':>8s} {'d10-19':>8s} {'d20-29':>8s} {'hires':>6s} {'land':>5s} {'hands':>6s} {'quads':>6s}")
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} {len(G[lab]):3d} {mean(lab, lambda r: r['final']):8,.0f} " + " ".join(f"{mean(lab, lambda r, i=i: r['truepos'][i]):8,.0f}" for i in range(3)) + f" {mean(lab, lambda r: r['hires']):6.1f} {mean(lab, lambda r: r['land']):5.1f} {mean(lab, lambda r: r['hands_end']):6.1f} {mean(lab, lambda r: r['quads']):6.1f}")
    print("\n== revenue by product x phase (mean coins)")
    print(f"{'group':10s} " + " ".join(f"{p[:5]}@{ph}" for p in PRODUCTS for ph in range(3) if p != "FERTILIZER"))
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} " + " ".join(f"{mean(lab, lambda r, k=f'{p}@{ph}': r['rev'][k]):7,.0f}" for p in PRODUCTS for ph in range(3) if p != "FERTILIZER"))
    print("\n== units sold by product x phase")
    for lab in labels:
        if not G[lab]: continue
        print(f"{lab:10s} " + " ".join(f"{mean(lab, lambda r, k=f'{p}@{ph}': r['units'][k]):7,.0f}" for p in PRODUCTS for ph in range(3) if p != "FERTILIZER"))
    print("\n== tile census (mean crop tiles / animals) at days " + str(DAYS))
    for lab in labels:
        if not G[lab]: continue
        row = []
        for d in DAYS:
            cr = {c: mean(lab, lambda r, c=c, d=d: r['census'][str(d)]['cr'].get(c, 0) if isinstance(list(r['census'].keys())[0], str) else r['census'][d]['cr'].get(c, 0)) for c in ("WHEAT", "CARROT", "STRAWBERRY", "TOMATO", "MELON")}
            an = mean(lab, lambda r, d=d: sum((r['census'][str(d)] if isinstance(list(r['census'].keys())[0], str) else r['census'][d])['an'].values()))
            row.append(f"d{d}: W{cr['WHEAT']:.0f} C{cr['CARROT']:.0f} S{cr['STRAWBERRY']:.0f} T{cr['TOMATO']:.0f} M{cr['MELON']:.0f} A{an:.0f}")
        print(f"{lab:10s} " + " | ".join(row))
