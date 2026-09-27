"""A/B: in towns with no YARN_STORE, from day SC_DAY stop FEED/CARE on sheep tiles (they escape after 2 unfed days) and drop
BUY_ANIMAL SHEEP orders. Wrapper on a chassis genome, paired seeds, both seats, vs mirror/demand/v31/v56. Env: SC_DAY=12.
Usage: CHASSIS=cha22 .venv/bin/python experiments/sheep_cut_ab.py <genome.json> [seeds=601-616] [jobs=8] [opps=mirror,demand,v31,v56]"""
import sys, os, json, statistics as st
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ.setdefault("CHASSIS", "cha22")
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
SC_DAY = int(os.environ.get("SC_DAY", "12"))
def _g(o, k, d=None):
    try: return o[k]
    except Exception: return getattr(o, k, d)
def wrap(inner):
    stats = {"cut": 0, "yarn_seen": False}
    def agent(obs, config=None):
        act = inner(obs, config)
        try:
            day = int(_g(obs, "day", 0)); shops = list(_g(_g(obs, "town", {}), "unlocked_shops", []) or [])
            if "YARN_STORE" in shops: stats["yarn_seen"] = True
            if day < SC_DAY or stats["yarn_seen"] or not isinstance(act, dict): return act
            player = int(_g(obs, "player", 0)); farm = _g(obs, "farms")[player]; tiles = _g(farm, "tiles")
            units = [list(_g(farm, "farmer"))] + [list(h) for h in _g(farm, "hands", [])]
            cmds = [list(act.get("farmer") or ["PASS"])] + [list(c) for c in (act.get("hands") or [])]
            for i, (pos, c) in enumerate(zip(units, cmds)):
                v = c[0] if c else None
                if v in ("FEED", "CARE") and pos:
                    x, y = int(pos[0]), int(pos[1]); t = tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[0]) else None
                    if isinstance(t, dict) and _g(t, "animal") == "SHEEP": cmds[i] = ["PASS"]; stats["cut"] += 1
            mk = [m for m in (act.get("market") or []) if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "SHEEP")]
            act = dict(act); act["farmer"], act["hands"], act["market"] = cmds[0], cmds[1:], mk
        except Exception: pass
        return act
    agent.stats = stats
    return agent
def play(job):
    variant, opp, seed, swap, gpath = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    g = json.load(open(gpath)); g = g.get("genome", g); genome = {**C.base_genome(), **{k: v for k, v in g.items() if k in C.SPACE}}
    a = C.make_agent(genome, tag="a"); a = wrap(a) if variant == "cut" else a
    b = C.make_agent(genome, tag="b") if opp == "mirror" else C.load_opp(opp)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([b, a] if swap else [a, b]); f = env.steps[-1]
    ra, rb = (f[1]["reward"], f[0]["reward"]) if swap else (f[0]["reward"], f[1]["reward"])
    yarn = "YARN_STORE" in env.steps[-1][0]["observation"]["town"]["unlocked_shops"]
    return variant, opp, seed, swap, ra, rb, getattr(a, "stats", {}).get("cut", 0), yarn
if __name__ == "__main__":
    gpath = sys.argv[1]; lo, hi = map(int, (sys.argv[2] if len(sys.argv) > 2 else "601-616").split("-")); jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    opps = (sys.argv[4] if len(sys.argv) > 4 else "mirror,demand,v31,v56").split(",")
    J = [(v, o, s, sw, gpath) for o in opps for s in range(lo, hi + 1) for sw in (0, 1) for v in (("cut",) if o == "mirror" else ("cut", "plain"))]
    print(f"SC_DAY={SC_DAY} games={len(J)}", flush=True)
    with ProcessPoolExecutor(jobs) as ex: res = list(ex.map(play, J, chunksize=1))
    print("yarn-store seeds:", sorted({s for _, _, s, _, _, _, _, y in res if y}), flush=True)
    for o in opps:
        for v in ("cut", "plain"):
            r = [x for x in res if x[0] == v and x[1] == o]
            if not r: continue
            print(f"{v:6s} vs {o:7s}: {sum(a > b for *_, a, b, _, _ in r)}-{sum(a < b for *_, a, b, _, _ in r)} margin {st.mean(a - b for *_, a, b, _, _ in r):+,.0f} ours {st.mean(a for *_, a, b, _, _ in r):,.0f} cut-actions/game {st.mean(c for *_, c, _ in r):.0f}", flush=True)
        if o != "mirror":
            g = {(s, sw): (a, y) for v, oo, s, sw, a, b, c, y in res if v == "cut" and oo == o}; p = {(s, sw): a for v, oo, s, sw, a, b, c, y in res if v == "plain" and oo == o}
            d = [(g[k][0] - p[k], g[k][1]) for k in g if k in p]
            ny = [x for x, y in d if not y]; yy = [x for x, y in d if y]
            print(f"   paired cut−plain own coins vs {o}: all {st.mean(x for x, _ in d):+,.0f} (wins {sum(x > 0 for x, _ in d)}-{sum(x < 0 for x, _ in d)}) | no-yarn seeds {st.mean(ny) if ny else 0:+,.0f} (n={len(ny)}) | yarn seeds {st.mean(yy) if yy else 0:+,.0f} (n={len(yy)})", flush=True)
