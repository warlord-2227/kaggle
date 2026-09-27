"""Labour and tile audit of v33's live games: per day, idle hand-steps (PASS / no-op), free tiles (None) by quadrant, distance from idle
hands to nearest free tile, seeds in stock, and low-value hand-steps (FEED/CARE on sheep in no-yarn towns).
Usage: .venv/bin/python analysis/scripts/labour_audit.py [jobs]"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT
def analyse(job):
    path, idx, label = job
    if label != "v33": return None
    try: R = json.load(open(path))
    except Exception: return None
    steps = R["steps"]
    if len(steps) < 720: return None
    idle = collections.Counter(); free = {}; dist = collections.defaultdict(list); lowval = collections.Counter(); seeds = {}
    yarn = "YARN_STORE" in steps[-1][0]["observation"]["town"]["unlocked_shops"]
    for t in range(719):
        o = steps[t][0]["observation"]; farm = o["farms"][idx]; day = o["day"]; tiles = farm["tiles"]
        a = steps[t + 1][idx].get("action") or {}
        units = [farm["farmer"]] + list(farm["hands"]); cmds = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        freetiles = [(x, y) for y in range(10) for x in range(10) if tiles[y][x] is None]
        if t % 24 == 12:
            free[day] = len(freetiles); seeds[day] = dict(steps[t][idx]["observation"]["private"]["seeds"])
        for pos, c in zip(units, cmds):
            v = c[0] if isinstance(c, (list, tuple)) and c else c
            if v == "PASS" or v is None:
                idle[day] += 1
                if freetiles and pos: dist[day].append(min(abs(pos[0] - x) + abs(pos[1] - y) for x, y in freetiles))
            elif v in ("FEED", "CARE") and pos and not yarn:
                x, y = pos; tt = tiles[y][x] if 0 <= y < 10 and 0 <= x < 10 else None
                if isinstance(tt, dict) and tt.get("animal") == "SHEEP": lowval[day] += 1
    return dict(yarn=yarn, idle=dict(idle), free=free, dist={d: st.mean(v) for d, v in dist.items() if v}, lowval=dict(lowval), seeds=seeds, hands=len(steps[-1][0]["observation"]["farms"][idx]["hands"]))
if __name__ == "__main__":
    J = [j for j in jobs() if j[2] == "v33"]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex: res = [r for r in ex.map(analyse, J) if r]
    json.dump(res, open(ROOT + "/analysis/data/labour_audit.json", "w"))
    print(f"games {len(res)}, hands at end {st.mean(r['hands'] for r in res):.1f}")
    print("day | idle hand-steps/day | free tiles (mid-day) | mean dist idle->free | sheep FEED/CARE steps (no-yarn towns) | tomato seeds")
    for d in range(0, 30):
        idle = st.mean(r["idle"].get(d, 0) for r in res); fr = st.mean(r["free"].get(d, 0) for r in res)
        ds = [r["dist"][d] for r in res if d in r["dist"]]; lv = [r["lowval"].get(d, 0) for r in res if not r["yarn"]]
        sd = st.mean(r["seeds"].get(d, {}).get("TOMATO", 0) for r in res)
        print(f"{d:3d} | {idle:6.1f} | {fr:5.1f} | {st.mean(ds) if ds else 0:5.1f} | {st.mean(lv) if lv else 0:5.1f} | {sd:4.1f}")
