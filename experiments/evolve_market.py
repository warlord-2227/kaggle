"""(mu+lambda) search over the market agent's knobs (kaggriculture/agents/market.py).

Genome = a subset of market.DEFAULT (ints/floats/bools) mutated within ranges; the agent is
market.make(**genome). Sparring: pass, the meta line (Cleo), v20 (our best grove), and the
market defaults as mirror. Seeds mix normal and no-strawberry-shop ("glut") draws.
Log: experiments/evolve_market_log.jsonl; best: experiments/evolve_market_best.json.
"""
import sys, os, json, random, time, statistics as st, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor

import trace_agent
# fitness = margin against REAL ladder opponents (replayed traces of agents rated 740-1033 that beat us),
# plus one pass game so absolute economy still counts. Rotates through the pool by generation.
def _pool(**kw):
    try: return trace_agent.pool(**kw)
    except FileNotFoundError: return []
TRACE_POOL = _pool(min_rating=700) + _pool(folder="mid") + _pool(folder="top")   # 700-1033 ladder + 1500-2500 mid tier + 3000 top tier
def bucket(rating): return "ladder" if rating < 1500 else ("mid" if rating < 2700 else "top")
OPPS = ["pass"] + [f"trace:{i}" for i in range(len(TRACE_POOL))]
# reactive public agents (Apache-2.0, refagents/public/): the only opponents that answer our market moves
PUB = {"farm2945": ROOT + "refagents/public/farm2945_v9_4.py", "shopwork": ROOT + "refagents/public/shopwork_tetsutani.py"}
PUB_OPPS = ["pub:%s" % k for k in PUB]
def load_pub(name):
    import importlib.util
    sp = importlib.util.spec_from_file_location("pub_" + name, PUB[name]); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m.agent
OPPS_PER_GEN = 12          # bigger per-generation sample: less elite drift
GLUT = [9002, 9006, 9007, 9028, 9034, 9038, 9048, 9050]
SPACE = {  # name: (kind, lo, hi)
    "cows_d0": ("int", 1, 3), "sheep_d0": ("int", 1, 4), "herd_ramp_day": ("int", 3, 8), "herd_until": ("int", 12, 20),
    "milk_prior": ("float", 0, 10), "milk_prior_early": ("float", 2, 14), "prior_until": ("int", 6, 16),
    "wool_prior": ("float", 0, 8), "cows_min": ("int", 2, 6), "cows_max": ("int", 6, 14), "sheep_min": ("int", 1, 5),
    "sheep_max": ("int", 4, 12), "geese_max": ("int", 0, 12), "geese_min": ("int", 0, 4), "npv_margin": ("int", -500, 4000), "herd_npv": ("int", 0, 1), "crop_value": ("int", 0, 1), "glut_pow": ("float", 0.3, 2.0), "glut_k": ("float", 0.8, 3.0), "npv_horizon_cut": ("int", 0, 6),
    "melon_tiles": ("int", 4, 16), "melon_until": ("int", 1, 22),
    "straw_prior": ("float", 0, 20), "straw_mult": ("float", 0.6, 1.8), "straw_min": ("int", 8, 24), "straw_max": ("int", 24, 48),
    "straw_until": ("int", 12, 20), "straw_rate": ("int", 4, 16), "straw_cash": ("int", 50, 600), "straw_priority_day": ("int", 2, 10),
    "wheat_mult": ("float", 0.3, 2.0), "wheat_feed_mult": ("float", 0.0, 3.0), "wheat_min": ("int", 4, 16), "wheat_max": ("int", 12, 50),
    "carrot_from": ("int", 4, 16), "carrot_max": ("int", 0, 24), "tomato_from": ("int", 4, 16), "tomato_max": ("int", 0, 12),
    "sprint_from": ("int", 15, 25), "sprint_until": ("int", 24, 27), "herd_reserve": ("int", 0, 900),
    "hands_day0": ("int", 3, 6), "hands_min": ("int", 3, 8), "hands_max": ("int", 8, 14), "work_per_unit": ("float", 4.0, 10.0),
    "feed_days": ("int", 1, 3), "cash_floor": ("int", 20, 300), "animals_per_day": ("int", 1, 10), "day0_wheat": ("int", 4, 14),
    "sell_chunk": ("int", 4, 14), "melon_chunk": ("int", 4, 12), "fert_reserve": ("int", 0, 4), "harvest_min_animal": ("int", 1, 3),
    "deliver_min": ("int", 300, 3000), "deliver_k": ("float", 0.1, 0.8), "deliver_min_early": ("int", 100, 1000), "deliver_early_until": ("int", 4, 14),
    "land_reserve": ("int", 0, 1500), "opp_weight": ("float", 0.0, 1.5),
    # 09-22: behaviours the top tier shows, as knobs (late herd growth when many milk buyers, tomato/carrot sizing,
    # goose activation, land timing/count, liquidation day)
    "herd_until2": ("int", 12, 26), "herd_rich_drain": ("int", 7, 25), "tomato_until": ("int", 14, 26), "carrot_mult": ("float", 0.4, 2.5),
    "tomato_mult": ("float", 0.4, 2.5), "egg_drain_min": ("int", 1, 13), "land_day1": ("int", 3, 12), "land_day2": ("int", 6, 18),
    "land_day3": ("int", 8, 22), "land_n": ("int", 1, 3), "liquidate_from": ("int", 26, 29),
    "harvest_decay": ("int", 0, 1), "harvest_late_hour": ("int", 12, 23), "shed_guard": ("int", 0, 1), "water_growth_mult": ("float", 0.5, 3.0),
}
from kaggriculture.agents import market as M
BASE = {k: M.DEFAULT[k] for k in SPACE}

def play(job):
    g, opp, seed = job
    import fair_env
    if not opp.startswith("trace:"):
        fair_env.apply()                        # agent-vs-agent / vs pass: same shops for both on a seed
    else:
        fair_env.restore()                      # traces need the SHIPPED env + their own seed to stay faithful (workers are reused!)
        seed = trace_agent.seed_of(TRACE_POOL[int(opp.split(":")[1])][1])
    from kaggle_environments import make as mk
    from kaggriculture.agents import market
    import importlib.util
    a = market.make(**g)
    if opp == "v20":
        sp = importlib.util.spec_from_file_location("m20", ROOT + "submissions/v20_grove_tuned2.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); b = m.agent
    elif opp in ("v21", "v22"):
        b = market.make(**json.load(open(ROOT + "experiments/%s_genome.json" % opp)))
    elif opp.startswith("trace:"):
        name, path, idx, rating = TRACE_POOL[int(opp.split(":")[1])]; b = trace_agent.make(path, idx)
    elif opp.startswith("pub:"):
        b = load_pub(opp.split(":")[1])
    else:
        b = opp
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]

SWITCHES = [k for k in ("herd_npv", "crop_value", "geese_min", "land_n", "harvest_decay", "shed_guard") if k in SPACE]

def mutate(g, rng, k=4):
    c = dict(g)
    if SWITCHES and rng.random() < 0.35:            # flip a structural switch in a third of the children
        key = rng.choice(SWITCHES); kind, lo, hi = SPACE[key]; c[key] = rng.randint(lo, hi)
    for key in rng.sample(list(SPACE), k):
        kind, lo, hi = SPACE[key]
        if kind == "int":
            span = max(1, (hi - lo) // 4); c[key] = min(hi, max(lo, c[key] + rng.randint(-span, span)))
        else:
            span = (hi - lo) / 4; c[key] = round(min(hi, max(lo, c[key] + rng.uniform(-span, span))), 2)
    return c

def evaluate(pop, seeds, ex, opps=None):
    opps = opps or OPPS
    jobs = [(g, o, s) for g in pop for o in opps for s in seeds]
    res = list(ex.map(play, jobs, chunksize=1))
    out = []; k = len(opps) * len(seeds)
    for i, g in enumerate(pop):
        r = res[i * k:(i + 1) * k]; by = {}
        for j, o in enumerate(opps):
            rr = r[j * len(seeds):(j + 1) * len(seeds)]
            label = o if not o.startswith("trace:") else TRACE_POOL[int(o.split(":")[1])][0]
            by[label] = round(st.mean(a - b for a, b in rr))
        out.append(dict(genome=g, margin=st.mean(a - b for a, b in r), wins=sum(a > b for a, b in r) / k, ours=st.mean(a for a, _ in r), by_opp=by))
    return out

def fullpool(genome, ex):
    """Margin vs every trace in TRACE_POOL on its native seed; per-bucket (wins, n, mean margin)."""
    full = ["trace:%d" % i for i in range(len(TRACE_POOL))]
    v = evaluate([genome], [0], ex, full)[0]
    out = {}
    for name, path, idx, rating in TRACE_POOL:
        out.setdefault(bucket(rating), []).append(v["by_opp"][name])
    res = {b: (sum(m > 0 for m in ms), len(ms), st.mean(ms)) for b, ms in out.items()}
    res["ours"] = v["ours"]; res["by_opp"] = v["by_opp"]
    if PUB_OPPS:
        seeds = [401, 402, 403, 404, 405, 406]
        pv = evaluate([genome], seeds, ex, PUB_OPPS)[0]
        n = len(PUB_OPPS) * len(seeds)
        res["pub"] = (round(pv["wins"] * n), n, pv["margin"]); res["by_opp"].update(pv["by_opp"])
    return res

def fmt(res):
    return " | ".join(f"{b} {w}/{n} {m:+,.0f}" for b, (w, n, m) in ((b, res[b]) for b in ("ladder", "mid", "top", "pub") if b in res)) + f" | ours {res['ours']:,.0f}"

if __name__ == "__main__":
    MU, LAM, SEEDS = 4, 12, 2
    RUN = sys.argv[1] if len(sys.argv) > 1 else "0"
    rng = random.Random(int(RUN))
    log = open(ROOT + "experiments/evolve_market_log.jsonl", "a")
    elites = [dict(genome=dict(BASE))]; gen = 0
    for f in ("experiments/v23_genome.json", "experiments/v22_genome.json", "experiments/evolve_market_best.json"):
        try:
            prev = json.load(open(ROOT + f)); prev = prev.get("genome", prev); prev = {k: v for k, v in prev.items() if k in SPACE}; elites.append(dict(genome={**BASE, **prev}))
        except Exception:
            pass
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 16))) as ex:
        while True:
            seeds = [rng.randrange(10**6) for _ in range(SEEDS - 1)] + [rng.choice(GLUT)]   # one glut seed per generation
            traces = rng.sample([o for o in OPPS if o.startswith("trace:")], OPPS_PER_GEN)
            opps = ["pass"] + traces + PUB_OPPS
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]; q = rng.choice(elites)["genome"]
                base = {k: (p[k] if rng.random() < 0.5 else q[k]) for k in p} if rng.random() < 0.3 else p
                children.append(mutate(base, rng))
            t0 = time.time(); scored = evaluate([e["genome"] for e in elites] + children, seeds, ex, opps)
            for s in scored: log.write(json.dumps(dict(gen=gen, seeds=seeds, **s)) + "\n")
            log.flush(); scored.sort(key=lambda s: -s["margin"]); elites = scored[:MU]; b = elites[0]
            json.dump(b, open(ROOT + "experiments/evolve_market_best.json", "w"), indent=1)
            if gen % 8 == 7:
                res = fullpool(b["genome"], ex)
                print(f"      FULL-POOL elite gen {gen}: {fmt(res)}", flush=True)
                json.dump(dict(gen=gen, genome=b["genome"], **{k: v for k, v in res.items() if k != "by_opp"}, by_opp=res["by_opp"]),
                          open(ROOT + "experiments/evolve_market_fullpool_%s_%03d.json" % (RUN, gen), "w"), indent=1)
            base_s = next((s for s in scored if s["genome"] == BASE), None)
            short = {k[:5]: v for k, v in b['by_opp'].items()}
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s best margin {b['margin']:>8,.0f} wins {b['wins']:.2f} ours {b['ours']:>8,.0f} {short} | base {round(base_s['margin']) if base_s else 'n/a'}", flush=True)
            # a candidate must also beat the whole pool better than the previous elite: track pool win-rate of the best
            print(f"      pool-wins {b['wins']:.2f} over {len(opps)-1} traces x {SEEDS} seeds", flush=True)
            print("     ", {k: v for k, v in b["genome"].items() if v != BASE[k]}, flush=True)
            gen += 1
