"""Yarn-store towns only: sheep tiles by day, wool units sold (shed deltas), realised wool price, CARE/FEED actions on sheep tiles,
sheep yield_units left uncollected. Usage: .venv/bin/python analysis/scripts/wool_gap.py [jobs]"""
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
    shops = steps[-1][0]["observation"]["town"].get("unlocked_shops", [])
    yarn = shops.count("YARN_STORE"); first_yarn = next((t for t in range(0, 720, 4) if "YARN_STORE" in steps[t][0]["observation"]["town"].get("unlocked_shops", [])), None)
    sheep = {}; care = feed = harv = 0; wool_units = 0; wool_rev = 0.0; wool_steps = 0; held = []
    for t in range(719):
        o = steps[t][0]["observation"]; farm = o["farms"][idx]; pr = steps[t][idx]["observation"]["private"]; pr1 = steps[t + 1][idx]["observation"]["private"]
        if t % 24 == 23:
            d = o["day"]; sh = [tt for row in farm["tiles"] for tt in row if isinstance(tt, dict) and tt.get("animal") == "SHEEP"]
            sheep[d] = len(sh); held.append(sum(tt.get("yield_units", 0) for tt in sh))
        a = steps[t + 1][idx].get("action") or {}
        # actions targeting sheep tiles: unit positions -> tile
        units = [farm["farmer"]] + list(farm["hands"]); cmds = [a.get("farmer") or []] + list(a.get("hands") or [])
        for pos, c in zip(units, cmds):
            v = c[0] if isinstance(c, (list, tuple)) and c else c
            if v in ("CARE", "FEED", "HARVEST") and pos:
                x, y = pos; tt = farm["tiles"][y][x] if 0 <= y < 10 and 0 <= x < 10 else None
                if isinstance(tt, dict) and tt.get("animal") == "SHEEP":
                    care += v == "CARE"; feed += v == "FEED"; harv += v == "HARVEST"
        m0 = farm["money"]; m1 = steps[t + 1][0]["observation"]["farms"][idx]["money"]
        orders = [m for m in (a.get("market") or []) if isinstance(m, (list, tuple)) and m]
        if orders and all(m[0] == "SELL" for m in orders) and any(m[1] == "WOOL" for m in orders if len(m) > 1):
            u = max(0, pr["shed"].get("WOOL", 0) - pr1["shed"].get("WOOL", 0))
            if u > 0 and len(orders) == 1: wool_units += u; wool_rev += m1 - m0; wool_steps += 1
    return dict(label=label, yarn=yarn, first_yarn=first_yarn, sheep=sheep, care=care, feed=feed, harv=harv, wool_units=wool_units, wool_rev=wool_rev, held=st.mean(held) if held else 0, final=R["rewards"][idx])
if __name__ == "__main__":
    J = jobs()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/wool_gap.json", "w"))
    G = collections.defaultdict(list)
    for r in res: G[(r["label"], r["yarn"] > 0)].append(r)
    print("group      yarn  n  sheep@d12 @d20 @d28 | CARE  FEED  HARV on sheep | wool units (pure-sell steps) rev/unit | uncollected wool/day | final")
    for lab in ["rank1", "rank1-opp", "top10", "band2900", "v33", "copies"]:
        for y in (True, False):
            r = G.get((lab, y), [])
            if not r: continue
            m = lambda f: st.mean(f(x) for x in r)
            U = sum(x["wool_units"] for x in r); RV = sum(x["wool_rev"] for x in r)
            print(f"{lab:10s} {str(y):5s} {len(r):2d}  {m(lambda x: x['sheep'].get(12, 0)):4.1f} {m(lambda x: x['sheep'].get(20, 0)):4.1f} {m(lambda x: x['sheep'].get(28, 0)):4.1f} | {m(lambda x: x['care']):5.0f} {m(lambda x: x['feed']):5.0f} {m(lambda x: x['harv']):5.0f} | {m(lambda x: x['wool_units']):6.0f} {RV / U if U else 0:6.0f} | {m(lambda x: x['held']):5.1f} | {m(lambda x: x['final']):8,.0f}")
    print("\nfirst yarn-store unlock step (yarn towns), mean:", {lab: st.mean(x["first_yarn"] for x in G.get((lab, True), []) if x["first_yarn"] is not None) for lab in ["rank1", "top10", "v33"] if G.get((lab, True))})
