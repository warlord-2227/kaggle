"""A/B: sale-metering wrapper on a chassis genome vs the unwrapped genome, paired seeds, both seats, vs mirror/demand/v31/v56.
Wrapper: for products in SG_PRODUCTS, drop SELL orders while quoted price < SG_ALPHA * base, unless day >= SG_END_DAY or shed
total >= SG_SHED (shed overflow destroys goods: DROP deletes what does not fit). Env: SG_ALPHA=0.8 SG_END_DAY=28 SG_SHED=70
SG_PRODUCTS=WOOL,STRAWBERRY,MILK,MELON SG_KEEP=0 (units still allowed per gated order). Usage:
CHASSIS=cha22 .venv/bin/python experiments/sell_gate_ab.py <genome.json> [seeds=601-616] [jobs=8] [opps=mirror,demand,v31,v56]"""
import sys, os, json, statistics as st
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ.setdefault("CHASSIS", "cha22")
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
ALPHA = float(os.environ.get("SG_ALPHA", "0.8")); END_DAY = int(os.environ.get("SG_END_DAY", "28")); SHED = int(os.environ.get("SG_SHED", "70"))
PRODS = set(os.environ.get("SG_PRODUCTS", "WOOL,STRAWBERRY,MILK,MELON").split(",")); KEEP = int(os.environ.get("SG_KEEP", "0"))
def _g(o, k, d=None):
    try: return o[k]
    except Exception: return getattr(o, k, d)
def wrap(inner):
    stats = {"held": 0, "kept": 0}
    def agent(obs, config=None):
        act = inner(obs, config)
        try:
            day = int(_g(obs, "day", 0)); prices = _g(_g(obs, "market", {}), "prices", {}); shed = dict(_g(_g(obs, "private", {}), "shed", {}) or {})
            tot = sum(int(v) for v in shed.values())
            if day >= END_DAY or tot >= SHED or not isinstance(act, dict): return act
            mk = act.get("market") or []; out = []
            for m in mk:
                if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL" and m[1] in PRODS and _g(prices, m[1], 0) < ALPHA * BASE[m[1]]:
                    stats["held"] += 1
                    if KEEP > 0: out.append([m[0], m[1], min(int(m[2]), KEEP)])
                    continue
                out.append(m)
            act = dict(act); act["market"] = out
        except Exception: pass
        return act
    agent.stats = stats
    return agent
def play(job):
    variant, opp, seed, swap, gpath = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    g = json.load(open(gpath)); g = g.get("genome", g); genome = {**C.base_genome(), **{k: v for k, v in g.items() if k in C.SPACE}}
    a = C.make_agent(genome, tag="a"); a = wrap(a) if variant == "gated" else a
    b = C.make_agent(genome, tag="b") if opp == "mirror" else C.load_opp(opp)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([b, a] if swap else [a, b]); f = env.steps[-1]
    ra, rb = (f[1]["reward"], f[0]["reward"]) if swap else (f[0]["reward"], f[1]["reward"])
    return variant, opp, seed, swap, ra, rb, getattr(a, "stats", {}).get("held", 0)
if __name__ == "__main__":
    gpath = sys.argv[1]; lo, hi = map(int, (sys.argv[2] if len(sys.argv) > 2 else "601-616").split("-")); jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    opps = (sys.argv[4] if len(sys.argv) > 4 else "mirror,demand,v31,v56").split(",")
    J = [(v, o, s, sw, gpath) for o in opps for s in range(lo, hi + 1) for sw in (0, 1) for v in (("gated",) if o == "mirror" else ("gated", "plain"))]
    print(f"ALPHA={ALPHA} END_DAY={END_DAY} SHED={SHED} PRODS={sorted(PRODS)} KEEP={KEEP} games={len(J)}", flush=True)
    with ProcessPoolExecutor(jobs) as ex: res = list(ex.map(play, J, chunksize=1))
    for o in opps:
        for v in ("gated", "plain"):
            r = [x for x in res if x[0] == v and x[1] == o]
            if not r: continue
            print(f"{v:6s} vs {o:7s}: {sum(a > b for *_, a, b, _ in r)}-{sum(a < b for *_, a, b, _ in r)} margin {st.mean(a - b for *_, a, b, _ in r):+,.0f} ours {st.mean(a for *_, a, b, _ in r):,.0f} held/game {st.mean(h for *_, h in r):.0f}", flush=True)
        if o != "mirror":
            g = {(s, sw): a for v, oo, s, sw, a, b, h in res if v == "gated" and oo == o}; p = {(s, sw): a for v, oo, s, sw, a, b, h in res if v == "plain" and oo == o}
            d = [g[k] - p[k] for k in g if k in p]; print(f"   paired gated−plain own coins vs {o}: {st.mean(d):+,.0f} (wins {sum(x > 0 for x in d)}-{sum(x < 0 for x in d)})", flush=True)
